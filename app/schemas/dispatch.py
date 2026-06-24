"""
Pydantic schemas for Dispatch Notes.

Like GRN, a Dispatch Note is created against a Sales Order, with line items.
Unlike GRN (which has a quality check step), dispatch is simpler: the
dispatched_qty is exactly what leaves stock, since there's no "quality
check" step on the way out -- only on the way in.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date, datetime


class DispatchItemCreate(BaseModel):
    item_id: int
    dispatched_qty: Decimal = Field(..., gt=0)


class DispatchItemResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    item_code: str
    dispatched_qty: Decimal

    class Config:
        from_attributes = True


class DispatchNoteCreate(BaseModel):
    dispatch_number: str = Field(..., max_length=50, examples=["DSP-2026-001"])
    so_id: int
    dispatch_date: date
    vehicle_number: str | None = Field(None, max_length=20)
    driver_name: str | None = Field(None, max_length=100)
    items: list[DispatchItemCreate] = Field(..., min_length=1, description="At least one item is required")


class DispatchNoteResponse(BaseModel):
    id: int
    dispatch_number: str
    so_id: int
    so_number: str
    warehouse_id: int
    warehouse_name: str
    dispatch_date: date
    vehicle_number: str | None
    driver_name: str | None
    created_by: int
    created_at: datetime
    items: list[DispatchItemResponse]

    class Config:
        from_attributes = True
