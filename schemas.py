"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    """A single line item in an order."""
    item_name: str = Field(..., description="Name of the product")
    quantity: float = Field(..., gt=0, description="Quantity ordered")
    unit: Optional[str] = Field(None, description="Unit (kg, pieces, boxes, etc.)")
    price_per_unit: Optional[float] = Field(None, ge=0, description="Price per unit")
    total_price: Optional[float] = Field(None, ge=0, description="Total price for this item")
    notes: Optional[str] = Field(None, description="Any extra notes for this item")

    @validator("item_name")
    def item_name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Item name cannot be empty")
        return v.strip().title()


class OrderRequest(BaseModel):
    """Incoming text order from a shopkeeper."""
    shopkeeper_name: Optional[str] = Field(None, description="Name of the shopkeeper")
    shopkeeper_phone: Optional[str] = Field(None, description="Phone number")
    raw_text: str = Field(..., description="Raw order text as received")
    source: Optional[str] = Field("api", description="Source: api, whatsapp, sms")


class ParsedOrder(BaseModel):
    """Fully parsed and validated order."""
    shopkeeper_name: Optional[str] = None
    shopkeeper_phone: Optional[str] = None
    items: List[OrderItem] = []
    source: str = "api"
    order_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raw_input: Optional[str] = None
    warnings: List[str] = []  # Validation warnings (missing price, etc.)


class OrderResponse(BaseModel):
    """API response after processing an order."""
    success: bool
    message: str
    order_id: Optional[str] = None
    items_processed: int = 0
    items_skipped: int = 0
    warnings: List[str] = []
    sheet_row: Optional[int] = None
    duplicate_detected: bool = False
