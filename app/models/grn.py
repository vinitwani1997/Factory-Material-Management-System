"""
Models for: grn, grn_items

A GRN (Goods Receipt Note) records material that has physically arrived at
a warehouse, against a specific Purchase Order. Quality check happens here:
each line item records how much was received vs. how much actually passed
inspection (accepted_qty) vs failed (rejected_qty). Only accepted_qty ever
gets added to stock.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class GRN(Base):
    __tablename__ = "grn"

    id = Column(Integer, primary_key=True, index=True)
    grn_number = Column(String(50), nullable=False, unique=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    invoice_doc_url = Column(String(255), nullable=True)  # uploaded supplier invoice/challan (file upload comes later)
    received_date = Column(Date, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder")
    warehouse = relationship("Warehouse")
    creator = relationship("User")
    items = relationship("GRNItem", back_populates="grn", cascade="all, delete-orphan")


class GRNItem(Base):
    __tablename__ = "grn_items"

    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("grn.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    received_qty = Column(Numeric(12, 2), nullable=False)
    accepted_qty = Column(Numeric(12, 2), nullable=False)
    rejected_qty = Column(Numeric(12, 2), nullable=False, default=0)
    batch_number = Column(String(50), nullable=True)  # for QR/barcode traceability later

    grn = relationship("GRN", back_populates="items")
    item = relationship("Item")
