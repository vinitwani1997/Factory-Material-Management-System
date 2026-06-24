"""
Pydantic schemas for Production Orders.

Flow:
  1. Create a production order with a `planned_qty` (status starts as "planned").
  2. Mark it "in_progress" when the production floor actually starts working on it.
  3. Complete it by providing the `actual_qty` produced (which may differ from
     planned_qty due to wastage or efficiency). Completing it is what triggers
     automatic raw material deduction and finished goods stock addition.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date, datetime
from typing import Literal


class ProductionOrderCreate(BaseModel):
    order_number: str = Field(..., max_length=50, examples=["PROD-2026-001"])
    bom_id: int
    warehouse_id: int
    planned_qty: Decimal = Field(..., gt=0)
    start_date: date | None = None


class ProductionOrderStatusUpdate(BaseModel):
    status: Literal["planned", "in_progress", "cancelled"]


class WastageInput(BaseModel):
    item_id: int
    wasted_qty: Decimal = Field(..., gt=0)
    reason: str | None = Field(None, max_length=255)


class ProductionOrderComplete(BaseModel):
    """Body for completing a production order -- this is what triggers stock movement."""
    actual_qty: Decimal = Field(..., gt=0, description="Actual finished quantity produced")
    end_date: date | None = None
    wastage: list[WastageInput] = Field(default_factory=list, description="Optional: any raw material wasted during this run")


class MaterialIssueResponse(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    issued_qty: Decimal

    class Config:
        from_attributes = True


class FGReceiptResponse(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    received_qty: Decimal

    class Config:
        from_attributes = True


class WastageResponse(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    wasted_qty: Decimal
    reason: str | None

    class Config:
        from_attributes = True


class ProductionOrderResponse(BaseModel):
    id: int
    order_number: str
    bom_id: int
    finished_item_id: int
    finished_item_name: str
    warehouse_id: int
    warehouse_name: str
    planned_qty: Decimal
    actual_qty: Decimal | None
    status: str
    start_date: date | None
    end_date: date | None
    created_by: int
    created_at: datetime
    material_issues: list[MaterialIssueResponse]
    fg_receipts: list[FGReceiptResponse]
    wastage_records: list[WastageResponse]

    class Config:
        from_attributes = True
