"""
Pydantic schemas for the Item Master.

These define what data the API accepts (request) and what it returns (response).
SQLAlchemy models (app/models/) define the DATABASE table.
Pydantic schemas (this file) define the API's INPUT/OUTPUT shape.
Keeping them separate is standard FastAPI practice.

Valid category values come from app/constants.py (ITEM_CATEGORY_VALUES) so
there is a single source of truth -- also exposed via GET /item-categories/
for the frontend to build a dropdown from.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal

from app.constants import ITEM_CATEGORY_VALUES

ItemCategory = Literal["raw_material", "semi_finished", "finished_good"]


class ItemCreate(BaseModel):
    """Fields required when creating a new item."""
    item_code: str = Field(..., max_length=50, examples=["RM-STEEL-001"])
    name: str = Field(..., max_length=150, examples=["Steel Sheet 2mm"])
    category: ItemCategory
    unit: str = Field(..., max_length=20, examples=["kg"])
    min_stock_level: Decimal = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    """Fields allowed when updating an item. All optional since it's a partial update."""
    name: str | None = None
    category: ItemCategory | None = None
    unit: str | None = None
    min_stock_level: Decimal | None = None


class ItemResponse(BaseModel):
    """What the API sends back."""
    id: int
    item_code: str
    name: str
    category: str
    unit: str
    min_stock_level: Decimal
    created_at: datetime

    class Config:
        from_attributes = True  # allows Pydantic to read data directly from SQLAlchemy objects
