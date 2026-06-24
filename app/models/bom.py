"""
Models for: boms, bom_items

A BOM (Bill of Materials) is the "recipe" for a finished/semi-finished item:
it lists exactly how much of each raw material is needed to produce ONE
unit of that item. A BOM can have multiple versions over time (e.g. if the
recipe changes), but only one version should be `is_active=True` at a time
for a given finished item.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class BOM(Base):
    __tablename__ = "boms"

    id = Column(Integer, primary_key=True, index=True)
    finished_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    version = Column(String(10), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True)

    finished_item = relationship("Item")
    bom_items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")


class BOMItem(Base):
    __tablename__ = "bom_items"

    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    raw_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    qty_required = Column(Numeric(12, 4), nullable=False)  # per ONE unit of the finished item

    bom = relationship("BOM", back_populates="bom_items")
    raw_item = relationship("Item")
