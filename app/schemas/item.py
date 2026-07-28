from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal


class ItemCreate(BaseModel):
    item_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    category: Literal["raw_material", "product"]
    unit: str = Field(..., max_length=20)
    min_stock_level: Decimal = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    name: str | None = None
    category: Literal["raw_material", "product"] | None = None
    unit: str | None = None
    min_stock_level: Decimal | None = None


class ItemResponse(BaseModel):
    id: int
    item_code: str
    name: str
    category: str
    unit: str
    min_stock_level: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
