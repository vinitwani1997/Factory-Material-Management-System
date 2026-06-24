"""
Models for: dispatch_notes, dispatch_items

A Dispatch Note records finished goods physically leaving the factory
against a Sales Order, including vehicle/gate-pass details. This is what
actually deducts stock (mirrors how GRN adds stock).
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class DispatchNote(Base):
    __tablename__ = "dispatch_notes"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_number = Column(String(50), nullable=False, unique=True, index=True)
    so_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    dispatch_date = Column(Date, nullable=False)
    vehicle_number = Column(String(20), nullable=True)
    driver_name = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sales_order = relationship("SalesOrder")
    warehouse = relationship("Warehouse")
    creator = relationship("User")
    items = relationship("DispatchItem", back_populates="dispatch_note", cascade="all, delete-orphan")


class DispatchItem(Base):
    __tablename__ = "dispatch_items"

    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("dispatch_notes.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    dispatched_qty = Column(Numeric(12, 2), nullable=False)

    dispatch_note = relationship("DispatchNote", back_populates="items")
    item = relationship("Item")
