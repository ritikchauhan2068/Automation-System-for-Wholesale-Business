"""
Analytics Router
Read order data back from Google Sheets for the dashboard.
Provides summary stats, recent orders, and per-shopkeeper breakdowns.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from app.services.sheets import get_sheets_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Column index mapping (0-based) matching sheets.py HEADERS
COL = {
    "order_id": 0,
    "date": 1,
    "shopkeeper_name": 2,
    "shopkeeper_phone": 3,
    "item_name": 4,
    "quantity": 5,
    "unit": 6,
    "price_per_unit": 7,
    "total_price": 8,
    "source": 9,
    "notes": 10,
    "warnings": 11,
}


def safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def fetch_all_rows() -> list[list]:
    """Fetch all data rows (excluding header) from the sheet."""
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.GOOGLE_SHEET_ID,
        range=f"{settings.GOOGLE_SHEET_NAME}!A2:L",
    ).execute()
    return result.get("values", [])


@router.get("/summary", summary="Overall order statistics")
async def get_summary():
    """
    Returns high-level stats: total orders, total revenue, top items, active shopkeepers.
    """
    try:
        rows = fetch_all_rows()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not read sheet: {e}")

    if not rows:
        return {"total_rows": 0, "unique_orders": 0, "total_revenue": 0, "shopkeepers": 0}

    order_ids = set()
    shopkeepers = set()
    total_revenue = 0.0
    item_counts: dict[str, float] = {}

    for row in rows:
        def g(col): return row[col] if len(row) > col else ""

        order_ids.add(g(COL["order_id"]))
        name = g(COL["shopkeeper_name"])
        if name:
            shopkeepers.add(name)
        total_revenue += safe_float(g(COL["total_price"]))

        item = g(COL["item_name"])
        qty = safe_float(g(COL["quantity"]))
        if item:
            item_counts[item] = item_counts.get(item, 0) + qty

    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_line_items": len(rows),
        "unique_orders": len(order_ids),
        "active_shopkeepers": len(shopkeepers),
        "total_revenue": round(total_revenue, 2),
        "top_items": [{"item": k, "total_qty": round(v, 2)} for k, v in top_items],
    }


@router.get("/recent", summary="Recent orders (last N days)")
async def get_recent_orders(days: int = Query(7, ge=1, le=90)):
    """
    Returns all order rows from the last N days, grouped by Order ID.
    """
    try:
        rows = fetch_all_rows()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not read sheet: {e}")

    cutoff = datetime.now() - timedelta(days=days)
    orders: dict[str, dict] = {}

    for row in rows:
        def g(col): return row[col] if len(row) > col else ""

        try:
            row_date = datetime.strptime(g(COL["date"])[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        if row_date < cutoff:
            continue

        oid = g(COL["order_id"])
        if oid not in orders:
            orders[oid] = {
                "order_id": oid,
                "date": g(COL["date"]),
                "shopkeeper_name": g(COL["shopkeeper_name"]),
                "shopkeeper_phone": g(COL["shopkeeper_phone"]),
                "source": g(COL["source"]),
                "items": [],
                "order_total": 0.0,
            }

        orders[oid]["items"].append({
            "item_name": g(COL["item_name"]),
            "quantity": safe_float(g(COL["quantity"])),
            "unit": g(COL["unit"]),
            "price_per_unit": safe_float(g(COL["price_per_unit"])),
            "total_price": safe_float(g(COL["total_price"])),
        })
        orders[oid]["order_total"] += safe_float(g(COL["total_price"]))

    result = list(orders.values())
    result.sort(key=lambda x: x["date"], reverse=True)

    return {
        "days": days,
        "order_count": len(result),
        "orders": result,
    }


@router.get("/shopkeeper/{name}", summary="Orders for a specific shopkeeper")
async def get_shopkeeper_orders(name: str):
    """
    Returns all orders and summary stats for a specific shopkeeper.
    """
    try:
        rows = fetch_all_rows()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not read sheet: {e}")

    matched = [
        row for row in rows
        if len(row) > COL["shopkeeper_name"]
        and row[COL["shopkeeper_name"]].lower() == name.lower()
    ]

    if not matched:
        return {"shopkeeper": name, "order_count": 0, "total_spent": 0, "items": []}

    total_spent = sum(safe_float(r[COL["total_price"]] if len(r) > COL["total_price"] else "0") for r in matched)
    unique_orders = len(set(r[COL["order_id"]] for r in matched if len(r) > COL["order_id"]))

    items = [
        {
            "date": r[COL["date"]] if len(r) > COL["date"] else "",
            "order_id": r[COL["order_id"]] if len(r) > COL["order_id"] else "",
            "item_name": r[COL["item_name"]] if len(r) > COL["item_name"] else "",
            "quantity": safe_float(r[COL["quantity"]] if len(r) > COL["quantity"] else "0"),
            "unit": r[COL["unit"]] if len(r) > COL["unit"] else "",
            "total_price": safe_float(r[COL["total_price"]] if len(r) > COL["total_price"] else "0"),
        }
        for r in matched
    ]

    return {
        "shopkeeper": name,
        "unique_orders": unique_orders,
        "total_line_items": len(matched),
        "total_spent": round(total_spent, 2),
        "items": items,
    }


@router.get("/shopkeepers", summary="List all shopkeepers")
async def list_shopkeepers():
    """Returns a list of all unique shopkeepers with order counts and total spend."""
    try:
        rows = fetch_all_rows()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not read sheet: {e}")

    summary: dict[str, dict] = {}
    for row in rows:
        def g(col): return row[col] if len(row) > col else ""
        name = g(COL["shopkeeper_name"])
        if not name:
            continue
        if name not in summary:
            summary[name] = {"name": name, "phone": g(COL["shopkeeper_phone"]), "order_ids": set(), "total_spent": 0.0}
        summary[name]["order_ids"].add(g(COL["order_id"]))
        summary[name]["total_spent"] += safe_float(g(COL["total_price"]))

    result = [
        {
            "name": v["name"],
            "phone": v["phone"],
            "total_orders": len(v["order_ids"]),
            "total_spent": round(v["total_spent"], 2),
        }
        for v in summary.values()
    ]
    result.sort(key=lambda x: x["total_spent"], reverse=True)
    return {"count": len(result), "shopkeepers": result}
