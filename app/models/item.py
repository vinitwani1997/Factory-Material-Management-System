"""
Model for: items (raw material, semi-finished, finished goods)

This is the most frequently referenced table in the whole system --
purchase orders, GRN, BOM, production, sales orders, dispatch, and the
stock ledger all point back to this table.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.database.connection import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(50), nullable=False, unique=True, index=True)  # used for QR/barcode
    name = Column(String(150), nullable=False)
    category = Column(String(20), nullable=False)  # "raw_material" | "semi_finished" | "finished_good"
    unit = Column(String(20), nullable=False)  # kg, litre, pcs, etc.
    min_stock_level = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
