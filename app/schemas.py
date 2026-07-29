"""
Pydantic schemas -- ye define karte hain ki API request/response mein
data kaisa dikhna chahiye (validation ke liye).
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ---------------- ITEM ----------------

class ItemCreate(BaseModel):
    name: str
    item_type: Literal["raw_material", "product"]
    unit: str = "pcs"


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None


class ItemOut(BaseModel):
    id: int
    name: str
    item_type: str
    unit: str
    current_stock: float
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- RAW MATERIAL IN ----------------

class RawMaterialInCreate(BaseModel):
    item_id: int
    quantity: float = Field(gt=0, description="Kitna raw material aaya (0 se zyada hona chahiye)")
    remarks: Optional[str] = None


# ---------------- PRODUCTION (Stock Production) ----------------

class ProductionCreate(BaseModel):
    raw_item_id: int
    raw_qty_consumed: float = Field(gt=0, description="Kitna raw material use hua")
    product_item_id: int
    product_qty_produced: float = Field(gt=0, description="Kitna product bana")
    remarks: Optional[str] = None


# ---------------- OUT MATERIAL ----------------

class OutMaterialCreate(BaseModel):
    item_id: int
    quantity: float = Field(gt=0, description="Kitna maal bahar gaya")
    remarks: Optional[str] = None


# ---------------- RETURN MATERIAL ----------------

class ReturnMaterialCreate(BaseModel):
    item_id: int
    quantity: float = Field(gt=0, description="Kitna maal wapas aaya")
    remarks: Optional[str] = None


# ---------------- TRANSACTION (history / list responses) ----------------

class TransactionOut(BaseModel):
    id: int
    item_id: int
    txn_type: str
    quantity: float
    reference_note: Optional[str] = None
    remarks: Optional[str] = None
    txn_date: datetime

    class Config:
        from_attributes = True


# ---------------- AVAILABLE MATERIAL (report) ----------------

class AvailableMaterialOut(BaseModel):
    item_id: int
    name: str
    item_type: str
    unit: str
    current_stock: float

    class Config:
        from_attributes = True
