"""
Pydantic schemas for Purchase Orders.

A PO is created with its items in a SINGLE request -- the frontend sends
one JSON payload containing the PO header info (supplier, warehouse) plus
a list of line items (item + quantity + rate). This is much easier for the
React form to work with than creating the PO first and adding items one by one.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal


# ---- Line item schemas ----

class POItemCreate(BaseModel):
    """One line item within a PO creation request."""
    item_id: int
    ordered_qty: Decimal = Field(..., gt=0, description="Must be greater than 0")
    rate: Decimal = Field(default=0, ge=0)


class POItemResponse(BaseModel):
    id: int
    item_id: int
    item_name: str  # filled in manually in the router for a friendlier response
    item_code: str
    ordered_qty: Decimal
    rate: Decimal

    class Config:
        from_attributes = True


# ---- Purchase Order schemas ----

class PurchaseOrderCreate(BaseModel):
    po_number: str = Field(..., max_length=50, examples=["PO-2026-001"])
    supplier_id: int
    warehouse_id: int
    items: list[POItemCreate] = Field(..., min_length=1, description="At least one item is required")


class PurchaseOrderStatusUpdate(BaseModel):
    status: Literal["pending", "partial", "completed", "cancelled"]


class PurchaseOrderResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    supplier_name: str
    warehouse_id: int
    warehouse_name: str
    status: str
    created_by: int
    created_at: datetime
    items: list[POItemResponse]

    class Config:
        from_attributes = True
