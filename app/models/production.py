"""
Models for: production_orders, material_issues, finished_goods_receipts, wastage_records

A Production Order represents one production run: "make X units of this
finished item, using this BOM, at this warehouse." When the order is marked
complete, the system:
  1. Issues (deducts) raw material from stock, based on the BOM x actual
     finished quantity produced (material_issues).
  2. Receives (adds) the finished goods into stock (finished_goods_receipts).
  3. Optionally records wastage if any material was lost/scrapped during the run.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class ProductionOrder(Base):
    __tablename__ = "production_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    planned_qty = Column(Numeric(12, 2), nullable=False)
    actual_qty = Column(Numeric(12, 2), nullable=True)  # filled in when the order is completed
    status = Column(String(20), nullable=False, default="planned")  # planned | in_progress | completed | cancelled
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bom = relationship("BOM")
    warehouse = relationship("Warehouse")
    creator = relationship("User")
    material_issues = relationship("MaterialIssue", back_populates="production_order", cascade="all, delete-orphan")
    fg_receipts = relationship("FinishedGoodsReceipt", back_populates="production_order", cascade="all, delete-orphan")
    wastage_records = relationship("WastageRecord", back_populates="production_order", cascade="all, delete-orphan")


class MaterialIssue(Base):
    """Raw material deducted from stock for a production run (created automatically on completion)."""
    __tablename__ = "material_issues"

    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    issued_qty = Column(Numeric(12, 2), nullable=False)
    issued_date = Column(DateTime(timezone=True), server_default=func.now())

    production_order = relationship("ProductionOrder", back_populates="material_issues")
    item = relationship("Item")


class FinishedGoodsReceipt(Base):
    """Finished goods added to stock from a production run (created automatically on completion)."""
    __tablename__ = "finished_goods_receipts"

    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    received_qty = Column(Numeric(12, 2), nullable=False)
    received_date = Column(DateTime(timezone=True), server_default=func.now())

    production_order = relationship("ProductionOrder", back_populates="fg_receipts")
    item = relationship("Item")


class WastageRecord(Base):
    __tablename__ = "wastage_records"

    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    wasted_qty = Column(Numeric(12, 2), nullable=False)
    reason = Column(String(255), nullable=True)

    production_order = relationship("ProductionOrder", back_populates="wastage_records")
    item = relationship("Item")
