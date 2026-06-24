"""
Model for: stock_ledger

This is THE most important table in the entire system. Every single stock
movement -- material coming in, material issued to production, finished
goods coming back, material going out for dispatch, transfers between
warehouses -- writes one row here. The current stock balance of any item
at any warehouse is calculated from this table.

Why a ledger (instead of just updating a "current_stock" number on the item)?
  1. Full audit trail -- you can see exactly when and why stock changed.
  2. balance_after gives a fast running total without recalculating from scratch.
  3. If something looks wrong, you can trace back through every transaction.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)

    # GRN_IN, PRODUCTION_ISSUE, FG_RECEIPT, DISPATCH_OUT, STOCK_TRANSFER_IN,
    # STOCK_TRANSFER_OUT, WASTAGE
    transaction_type = Column(String(30), nullable=False)

    # id of the GRN / dispatch / production order etc. that caused this entry
    # (not a strict foreign key, since it can point to different tables depending on transaction_type)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String(30), nullable=True)  # e.g. "GRN", "DISPATCH" - which table reference_id points to

    quantity = Column(Numeric(12, 2), nullable=False)         # positive = stock IN, negative = stock OUT
    balance_after = Column(Numeric(12, 2), nullable=False)    # running balance for this item+warehouse after this entry

    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("Item")
    warehouse = relationship("Warehouse")
