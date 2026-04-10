"""
Orders API Router
Handles text orders, file uploads, and order retrieval endpoints.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional

from app.models.schemas import OrderRequest, OrderResponse
from app.services.parser import parse_order
from app.services.sheets import insert_order
from app.services.extractor import extract_text_from_file
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/text", response_model=OrderResponse, summary="Submit a text order")
async def submit_text_order(request: OrderRequest):
    """
    Accept a raw text order from a shopkeeper and process it.

    **Example input:**
    ```
    Sugar 5 kg @40
    Rice 10 kg 35
    Cooking Oil 3 litre 120
    ```
    """
    logger.info(f"Text order received from: {request.shopkeeper_name}")

    # Step 1: Parse the raw text
    try:
        parsed = parse_order(request)
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to parse order: {e}")

    if not parsed.items:
        return OrderResponse(
            success=False,
            message="No valid order items could be extracted from the input.",
            warnings=parsed.warnings,
        )

    # Step 2: Insert into Google Sheets
    try:
        result = insert_order(parsed)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Step 3: Return response
    if result.get("duplicate"):
        return OrderResponse(
            success=False,
            message=result["message"],
            order_id=result["order_id"],
            duplicate_detected=True,
            warnings=parsed.warnings,
        )

    return OrderResponse(
        success=True,
        message=result["message"],
        order_id=result["order_id"],
        items_processed=result["rows_inserted"],
        items_skipped=len(parsed.items) - result["rows_inserted"],
        warnings=parsed.warnings,
    )


@router.post("/file", response_model=OrderResponse, summary="Upload a PDF or image order")
async def submit_file_order(
    file: UploadFile = File(..., description="PDF, PNG, JPG, or TXT file"),
    shopkeeper_name: Optional[str] = Form(None),
    shopkeeper_phone: Optional[str] = Form(None),
    source: Optional[str] = Form("file_upload"),
):
    """
    Accept a file upload (PDF or image), extract text via OCR, then process as an order.
    """
    logger.info(f"File order received: {file.filename} from {shopkeeper_name}")

    # Validate file size
    file_bytes = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Step 1: Extract text
    try:
        raw_text = extract_text_from_file(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from the file.")

    logger.info(f"Extracted text from file:\n{raw_text[:200]}...")

    # Step 2: Re-use the text order pipeline
    order_request = OrderRequest(
        shopkeeper_name=shopkeeper_name,
        shopkeeper_phone=shopkeeper_phone,
        raw_text=raw_text,
        source=source,
    )

    try:
        parsed = parse_order(order_request)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse extracted text: {e}")

    if not parsed.items:
        return OrderResponse(
            success=False,
            message="No valid order items found in the file.",
            warnings=parsed.warnings,
        )

    try:
        result = insert_order(parsed)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if result.get("duplicate"):
        return OrderResponse(
            success=False,
            message=result["message"],
            order_id=result["order_id"],
            duplicate_detected=True,
            warnings=parsed.warnings,
        )

    return OrderResponse(
        success=True,
        message=result["message"],
        order_id=result["order_id"],
        items_processed=result["rows_inserted"],
        items_skipped=len(parsed.items) - result["rows_inserted"],
        warnings=parsed.warnings,
    )


@router.post("/parse-preview", summary="Preview parsed order without saving")
async def preview_parse(request: OrderRequest):
    """
    Parse a text order and return the structured result WITHOUT saving to Google Sheets.
    Useful for testing and debugging.
    """
    try:
        parsed = parse_order(request)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "shopkeeper_name": parsed.shopkeeper_name,
        "items": [item.dict() for item in parsed.items],
        "item_count": len(parsed.items),
        "warnings": parsed.warnings,
        "raw_input_preview": parsed.raw_input[:300] if parsed.raw_input else "",
    }
