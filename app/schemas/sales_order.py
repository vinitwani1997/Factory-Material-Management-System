"""
Pydantic schemas for Sales Orders. Mirrors Purchase Order schemas, but for
the outward (customer-facing) side.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal


class SOItemCreate(BaseModel):
    item_id: int
    ordered_qty: Decimal = Field(..., gt=0)
    rate: Decimal = Field(default=0, ge=0)


class SOItemResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    item_code: str
    ordered_qty: Decimal
    rate: Decimal

    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    so_number: str = Field(..., max_length=50, examples=["SO-2026-001"])
    customer_id: int
    warehouse_id: int
    items: list[SOItemCreate] = Field(..., min_length=1, description="At least one item is required")


class SalesOrderStatusUpdate(BaseModel):
    status: Literal["pending", "partial", "completed", "cancelled"]


class SalesOrderResponse(BaseModel):
    id: int
    so_number: str
    customer_id: int
    customer_name: str
    warehouse_id: int
    warehouse_name: str
    status: str
    created_by: int
    created_at: datetime
    items: list[SOItemResponse]

    class Config:
        from_attributes = True
