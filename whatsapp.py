"""
WhatsApp Webhook Router (Twilio)
Receives incoming WhatsApp messages and processes them as orders automatically.

Setup:
  1. Get a Twilio account + WhatsApp sandbox number
  2. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN in .env
  3. Point Twilio webhook URL to: POST /api/v1/whatsapp/incoming
"""

import logging
import hmac
import hashlib
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import PlainTextResponse

from app.models.schemas import OrderRequest
from app.services.parser import parse_order
from app.services.sheets import insert_order
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_twilio_signature(request_url: str, post_params: dict, signature: str) -> bool:
    """
    Validate that the webhook came from Twilio (not a spoofed request).
    https://www.twilio.com/docs/usage/webhooks/webhooks-security
    """
    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_AUTH_TOKEN not set — skipping signature validation")
        return True

    # Build the validation string: URL + sorted POST params
    s = request_url
    if post_params:
        s += "".join(f"{k}{v}" for k, v in sorted(post_params.items()))

    mac = hmac.new(
        settings.TWILIO_AUTH_TOKEN.encode("utf-8"),
        s.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    import base64
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def build_twiml_response(message: str) -> str:
    """Build a TwiML XML response to send back to the WhatsApp sender."""
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{safe}</Message>
</Response>"""


@router.post("/incoming", response_class=PlainTextResponse, summary="Twilio WhatsApp webhook")
async def whatsapp_incoming(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    ProfileName: str = Form(default=""),
    NumMedia: str = Form(default="0"),
):
    """
    Twilio sends incoming WhatsApp messages here as form POST data.
    Fields: Body (message text), From (sender number), ProfileName (WA display name).
    """
    # Optional: validate Twilio signature in production
    # signature = request.headers.get("X-Twilio-Signature", "")
    # if not verify_twilio_signature(str(request.url), dict(await request.form()), signature):
    #     raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    sender_phone = From.replace("whatsapp:", "").strip()
    sender_name = ProfileName.strip() or f"WA-{sender_phone[-4:]}"

    logger.info(f"WhatsApp message from {sender_name} ({sender_phone}): {Body[:80]}...")

    if not Body.strip():
        return PlainTextResponse(
            build_twiml_response("Hi! Please send your order as a list. Example:\nSugar 5 kg @40\nRice 10 kg 35"),
            media_type="text/xml",
        )

    # Greetings — don't try to parse as an order
    greetings = {"hi", "hello", "hii", "hey", "namaste", "helo"}
    if Body.strip().lower() in greetings:
        reply = (
            f"Hello {sender_name}! 👋\n\n"
            "To place an order, just send your list like this:\n"
            "Sugar 5 kg @40\n"
            "Rice 10 kg 35\n"
            "Oil 3 litre 120\n\n"
            "I'll automatically save it for you."
        )
        return PlainTextResponse(build_twiml_response(reply), media_type="text/xml")

    # Parse and store the order
    order_request = OrderRequest(
        shopkeeper_name=sender_name,
        shopkeeper_phone=sender_phone,
        raw_text=Body,
        source="whatsapp",
    )

    try:
        parsed = parse_order(order_request)

        if not parsed.items:
            reply = (
                "❌ Sorry, I couldn't read any items from your message.\n\n"
                "Please use this format:\n"
                "Item Name  Quantity  Unit  Price\n"
                "Example: Sugar 5 kg @40"
            )
            return PlainTextResponse(build_twiml_response(reply), media_type="text/xml")

        result = insert_order(parsed)

        if result.get("duplicate"):
            reply = f"⚠️ This order was already received (ID: {result['order_id']}). No duplicate saved."
        else:
            items_summary = "\n".join(
                f"• {item.item_name} — {item.quantity} {item.unit or ''}"
                + (f" @ ₹{item.price_per_unit}" if item.price_per_unit else "")
                for item in parsed.items
            )
            warning_note = ""
            if parsed.warnings:
                missing = [w for w in parsed.warnings if "Price missing" in w]
                if missing:
                    warning_note = f"\n\n⚠️ Price missing for {len(missing)} item(s). Please confirm."

            reply = (
                f"✅ Order saved! (ID: {result['order_id']})\n\n"
                f"{items_summary}"
                f"{warning_note}"
            )

    except Exception as e:
        logger.error(f"WhatsApp order processing failed: {e}")
        reply = "❌ Something went wrong saving your order. Please try again or contact support."

    return PlainTextResponse(build_twiml_response(reply), media_type="text/xml")


@router.get("/status", summary="WhatsApp webhook health check")
async def whatsapp_status():
    """Twilio pings this to verify the webhook URL is reachable."""
    return {"status": "ok", "webhook": "active"}
