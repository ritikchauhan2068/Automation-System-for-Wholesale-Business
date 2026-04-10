"""
Google Sheets Integration Service
Handles authentication, header setup, duplicate detection, and row insertion.
"""

import logging
import hashlib
from datetime import datetime
from typing import List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.models.schemas import ParsedOrder, OrderItem

logger = logging.getLogger(__name__)

# Required OAuth scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column headers for the Google Sheet
HEADERS = [
    "Order ID",
    "Date",
    "Shopkeeper Name",
    "Shopkeeper Phone",
    "Item Name",
    "Quantity",
    "Unit",
    "Price Per Unit (₹)",
    "Total Price (₹)",
    "Source",
    "Notes",
    "Warnings",
]


def get_sheets_service():
    """Authenticate and return the Google Sheets API service."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_PATH,
            scopes=SCOPES,
        )
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return service
    except FileNotFoundError:
        raise RuntimeError(
            f"Google credentials file not found at: {settings.GOOGLE_SHEETS_CREDENTIALS_PATH}\n"
            "Please follow the setup guide to create and place your credentials."
        )
    except Exception as e:
        logger.error(f"Google Sheets auth failed: {e}")
        raise


def ensure_headers(service, spreadsheet_id: str, sheet_name: str):
    """
    Check if header row exists. If not, create it.
    Also creates the worksheet tab if missing.
    """
    try:
        # Try reading the first row
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:Z1",
        ).execute()

        existing = result.get("values", [[]])[0] if result.get("values") else []

        if not existing:
            # Insert headers
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()
            logger.info(f"Headers created in sheet '{sheet_name}'")
        else:
            logger.debug("Headers already exist")

    except HttpError as e:
        if "Unable to parse range" in str(e) or "not found" in str(e).lower():
            # Sheet tab doesn't exist — create it
            _create_sheet_tab(service, spreadsheet_id, sheet_name)
            ensure_headers(service, spreadsheet_id, sheet_name)
        else:
            raise


def _create_sheet_tab(service, spreadsheet_id: str, sheet_name: str):
    """Add a new worksheet tab to the spreadsheet."""
    body = {
        "requests": [{
            "addSheet": {
                "properties": {"title": sheet_name}
            }
        }]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body,
    ).execute()
    logger.info(f"Created new sheet tab: '{sheet_name}'")


def generate_order_id(shopkeeper: Optional[str], items: List[OrderItem]) -> str:
    """Generate a short unique order ID based on shopkeeper + items."""
    fingerprint = f"{shopkeeper}|{'|'.join(i.item_name for i in items)}"
    return "ORD-" + hashlib.md5(fingerprint.encode()).hexdigest()[:8].upper()


def check_duplicate(service, spreadsheet_id: str, sheet_name: str, order_id: str) -> bool:
    """
    Check if an order with the same ID already exists in the sheet.
    Compares against Column A (Order ID).
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:A",
        ).execute()
        existing_ids = [row[0] for row in result.get("values", []) if row]
        return order_id in existing_ids
    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return False  # On error, allow insertion


def insert_order(parsed_order: ParsedOrder) -> dict:
    """
    Main function: validates, checks duplicates, inserts into Google Sheets.
    Returns a result dict with row info and status.
    """
    service = get_sheets_service()
    sheet_id = settings.GOOGLE_SHEET_ID
    sheet_name = settings.GOOGLE_SHEET_NAME

    ensure_headers(service, sheet_id, sheet_name)

    order_id = generate_order_id(parsed_order.shopkeeper_name, parsed_order.items)

    # Duplicate detection
    if check_duplicate(service, sheet_id, sheet_name, order_id):
        logger.warning(f"Duplicate order detected: {order_id}")
        return {
            "success": False,
            "duplicate": True,
            "order_id": order_id,
            "message": f"Duplicate order detected (ID: {order_id}). Not inserted.",
            "rows_inserted": 0,
        }

    # Build rows — one row per item
    rows = []
    for item in parsed_order.items:
        row = [
            order_id,
            parsed_order.order_date,
            parsed_order.shopkeeper_name or "",
            parsed_order.shopkeeper_phone or "",
            item.item_name,
            item.quantity,
            item.unit or "",
            item.price_per_unit if item.price_per_unit is not None else "",
            item.total_price if item.total_price is not None else "",
            parsed_order.source,
            item.notes or "",
            "; ".join(parsed_order.warnings) if parsed_order.warnings else "",
        ]
        rows.append(row)

    if not rows:
        return {
            "success": False,
            "duplicate": False,
            "order_id": order_id,
            "message": "No valid items found to insert",
            "rows_inserted": 0,
        }

    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

        updated_range = result.get("updates", {}).get("updatedRange", "")
        logger.info(f"Inserted {len(rows)} rows for order {order_id} → {updated_range}")

        return {
            "success": True,
            "duplicate": False,
            "order_id": order_id,
            "message": f"Inserted {len(rows)} item(s) into Google Sheets",
            "rows_inserted": len(rows),
            "updated_range": updated_range,
        }

    except HttpError as e:
        logger.error(f"Google Sheets insert failed: {e}")
        raise RuntimeError(f"Google Sheets API error: {e}")
