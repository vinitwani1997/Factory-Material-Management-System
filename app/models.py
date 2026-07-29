"""
Only 2 tables in this whole simplified system:

1. Item              -> Har Raw Material aur har Product ki master entry.
                         Ismein current_stock field direct maintained hoti hai
                         (yani stock number seedha yahin update hota hai, alag
                         se calculate nahi karna padta).

2. StockTransaction   -> Har stock movement ka history/log (audit trail ke liye).
                         Isse pata chalta hai KAB, KITNA, KIS type ka movement hua.
                         (Ye sirf record ke liye hai, current stock Item table se hi
                         seedha padha jaata hai — fast aur simple.)
"""

import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class ItemType(str, enum.Enum):
    raw_material = "raw_material"   # Kacha maal (jo bahar se aata hai)
    product = "product"             # Bana hua maal (jo production se banta hai)


class TransactionType(str, enum.Enum):
    RAW_MATERIAL_IN = "RAW_MATERIAL_IN"   # Raw material factory mein aaya       (+ stock)
    PRODUCTION_CONSUME = "PRODUCTION_CONSUME"  # Raw material production mein use hua (- stock)
    PRODUCTION_ADD = "PRODUCTION_ADD"     # Production se product bana           (+ stock)
    OUT_MATERIAL = "OUT_MATERIAL"         # Maal bahar gaya (sale/dispatch)      (- stock)
    RETURN_MATERIAL = "RETURN_MATERIAL"   # Maal wapas aaya                     (+ stock)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    item_type = Column(Enum(ItemType), nullable=False)
    unit = Column(String, nullable=False, default="pcs")   # kg, pcs, litre, etc.

    # Current available stock -- seedha yahin update hota hai har transaction par.
    current_stock = Column(Float, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("StockTransaction", back_populates="item")


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)

    txn_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)   # hamesha positive number store hota hai

    # Production wale transaction ko ek dusre se link karne ke liye
    # (jaise "produce kiya X ko consume karke Y product bana")
    reference_note = Column(String, nullable=True)

    remarks = Column(Text, nullable=True)
    txn_date = Column(DateTime, default=datetime.utcnow)

    item = relationship("Item", back_populates="transactions")
