"""
Pydantic schemas for BOM (Bill of Materials).

A BOM is created with its raw material requirements in a SINGLE request:
the finished item it produces, plus a list of raw materials and how much
of each is needed per ONE unit of that finished item.
"""

from pydantic import BaseModel, Field
from decimal import Decimal


# ---- Line item schemas ----

class BOMItemCreate(BaseModel):
    raw_item_id: int
    qty_required: Decimal = Field(..., gt=0, description="Quantity of this raw material needed per 1 unit of the finished item")


class BOMItemResponse(BaseModel):
    id: int
    raw_item_id: int
    raw_item_name: str
    raw_item_code: str
    unit: str
    qty_required: Decimal

    class Config:
        from_attributes = True


# ---- BOM schemas ----

class BOMCreate(BaseModel):
    finished_item_id: int
    version: str = Field(default="1.0", max_length=10)
    bom_items: list[BOMItemCreate] = Field(..., min_length=1, description="At least one raw material is required")


class BOMResponse(BaseModel):
    id: int
    finished_item_id: int
    finished_item_name: str
    finished_item_code: str
    version: str
    is_active: bool
    bom_items: list[BOMItemResponse]

    class Config:
        from_attributes = True
