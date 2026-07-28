from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, nullable=False)

    # STOCK_IN, PRODUCTION, STOCK_OUT, RETURN_FROM_CUSTOMER, RETURN_TO_SUPPLIER
    transaction_type = Column(String(30), nullable=False)

    quantity = Column(Numeric(12, 2), nullable=False)       # positive = IN, negative = OUT
    balance_after = Column(Numeric(12, 2), nullable=False)  # running balance after this entry

    note = Column(Text, nullable=True)                      # optional reason / reference
    created_by = Column(Integer, nullable=True)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())
