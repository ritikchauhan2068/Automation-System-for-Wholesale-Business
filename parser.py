"""
Order Parser Service
Converts messy raw text into structured OrderItem list.
Supports both rule-based regex parsing and optional LLM-powered parsing.
"""

import re
import logging
from typing import List, Tuple, Optional
from app.models.schemas import OrderItem, ParsedOrder, OrderRequest
from app.core.config import settings

logger = logging.getLogger(__name__)

# Common unit aliases (normalize various spellings)
UNIT_MAP = {
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg",
    "g": "g", "gm": "g", "gram": "g", "grams": "g",
    "l": "L", "ltr": "L", "litre": "L", "liter": "L", "litres": "L",
    "ml": "ml",
    "pcs": "pcs", "pc": "pcs", "piece": "pcs", "pieces": "pcs",
    "box": "box", "boxes": "box", "bx": "box",
    "doz": "doz", "dozen": "doz",
    "bag": "bag", "bags": "bag",
    "pkt": "pkt", "packet": "pkt", "packets": "pkt",
    "carton": "carton", "ctn": "carton",
}

# Regex pattern to detect a line item
# Matches: "Sugar 5 kg @40" or "5 kg Sugar 40rs" or "Basmati Rice - 10 bags - 550"
LINE_PATTERN = re.compile(
    r"""
    (?P<item>[A-Za-z][A-Za-z0-9\s\-_/]{1,50}?)   # Item name
    \s*[-:,]?\s*
    (?P<qty>\d+(?:\.\d+)?)                         # Quantity (e.g., 5 or 2.5)
    \s*
    (?P<unit>kg|kgs|kilo|g|gm|gram|l|ltr|litre|liter|ml|pcs|pc|piece|pieces|box|boxes|bx|doz|dozen|bag|bags|pkt|packet|carton|ctn)?
    \s*[-,@]?\s*
    (?:(?:rs|₹|inr|price|@|rate)[\s.]?)?          # Optional price prefix
    (?P<price>\d+(?:\.\d+)?)?                      # Price (optional)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    if not raw_unit:
        return None
    return UNIT_MAP.get(raw_unit.lower(), raw_unit.lower())


def parse_with_regex(raw_text: str) -> Tuple[List[OrderItem], List[str]]:
    """
    Rule-based parser using regex.
    Returns (items, warnings).
    """
    items: List[OrderItem] = []
    warnings: List[str] = []
    lines = raw_text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # Skip lines that look like headers or labels
        if re.match(r"^(order|from|to|date|shop|name|phone|mob|whatsapp|dear|hi|hello)\b", line, re.I):
            continue

        match = LINE_PATTERN.search(line)
        if match:
            item_name = match.group("item").strip().strip("-:, ")
            qty_str = match.group("qty")
            unit_raw = match.group("unit")
            price_str = match.group("price")

            if not item_name or len(item_name) < 2:
                continue

            try:
                qty = float(qty_str)
            except (TypeError, ValueError):
                warnings.append(f"Could not parse quantity in line: '{line}'")
                continue

            unit = normalize_unit(unit_raw)

            price = None
            total = None
            if price_str:
                try:
                    price = float(price_str)
                    total = round(price * qty, 2)
                except ValueError:
                    warnings.append(f"Could not parse price in line: '{line}'")

            if price is None:
                warnings.append(f"Price missing for '{item_name}' — please verify")

            items.append(OrderItem(
                item_name=item_name,
                quantity=qty,
                unit=unit,
                price_per_unit=price,
                total_price=total,
            ))
        else:
            warnings.append(f"Could not parse line: '{line}'")

    return items, warnings


def parse_with_llm(raw_text: str) -> Tuple[List[OrderItem], List[str]]:
    """
    LLM-powered parser using OpenAI.
    Fallback to regex if OpenAI is unavailable.
    """
    try:
        from openai import OpenAI
        import json

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = f"""
You are an order parsing assistant for a wholesale business.
Extract all order line items from the text below.

Return ONLY a valid JSON array with this structure (no markdown, no explanation):
[
  {{"item_name": "Sugar", "quantity": 5, "unit": "kg", "price_per_unit": 40, "total_price": 200}},
  ...
]

Rules:
- If price is missing, use null
- If unit is missing, use null
- item_name must be a proper product name
- quantity must be a number

Order text:
\"\"\"
{raw_text}
\"\"\"
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000,
        )

        raw_json = response.choices[0].message.content.strip()
        raw_json = re.sub(r"```json|```", "", raw_json).strip()
        parsed = json.loads(raw_json)

        items = []
        warnings = []
        for entry in parsed:
            try:
                item = OrderItem(
                    item_name=entry.get("item_name", "Unknown"),
                    quantity=float(entry.get("quantity", 1)),
                    unit=entry.get("unit"),
                    price_per_unit=entry.get("price_per_unit"),
                    total_price=entry.get("total_price"),
                )
                items.append(item)
                if not item.price_per_unit:
                    warnings.append(f"Price missing for '{item.item_name}'")
            except Exception as e:
                warnings.append(f"Skipped invalid entry: {entry} — {e}")

        logger.info(f"LLM parsed {len(items)} items")
        return items, warnings

    except Exception as e:
        logger.warning(f"LLM parsing failed ({e}), falling back to regex")
        return parse_with_regex(raw_text)


def parse_order(request: OrderRequest) -> ParsedOrder:
    """
    Main entry point. Chooses LLM or regex based on config.
    """
    logger.info(f"Parsing order from '{request.shopkeeper_name}' via {request.source}")

    if settings.USE_LLM_PARSING and settings.OPENAI_API_KEY:
        items, warnings = parse_with_llm(request.raw_text)
    else:
        items, warnings = parse_with_regex(request.raw_text)

    logger.info(f"Parsed {len(items)} items, {len(warnings)} warnings")

    return ParsedOrder(
        shopkeeper_name=request.shopkeeper_name,
        shopkeeper_phone=request.shopkeeper_phone,
        items=items,
        source=request.source or "api",
        raw_input=request.raw_text,
        warnings=warnings,
    )
