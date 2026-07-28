from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal


class StockInCreate(BaseModel):
    """Raw material coming IN (from supplier / purchase)."""
    item_id: int
    quantity: Decimal = Field(..., gt=0)
    note: str | None = None


class ProductionCreate(BaseModel):
    """Production entry: raw materials used → product made."""
    raw_material_id: int
    raw_qty_used: Decimal = Field(..., gt=0)
    product_id: int
    product_qty_made: Decimal = Field(..., gt=0)
    note: str | None = None


class StockOutCreate(BaseModel):
    """Material going OUT (to customer / dispatch)."""
    item_id: int
    quantity: Decimal = Field(..., gt=0)
    note: str | None = None


class ReturnCreate(BaseModel):
    """Return material - from customer or back to supplier."""
    item_id: int
    quantity: Decimal = Field(..., gt=0)
    return_type: Literal["return_from_customer", "return_to_supplier"]
    note: str | None = None


class StockLedgerResponse(BaseModel):
    id: int
    item_id: int
    transaction_type: str
    quantity: Decimal
    balance_after: Decimal
    note: str | None
    created_by: int | None
    transaction_date: datetime

    class Config:
        from_attributes = True


class AvailableStockRow(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    category: str
    unit: str
    current_stock: Decimal
    min_stock_level: Decimal
    is_low_stock: bool
