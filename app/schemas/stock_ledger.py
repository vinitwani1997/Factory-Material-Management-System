from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


class StockLedgerEntryResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    item_code: str
    warehouse_id: int
    warehouse_name: str
    transaction_type: str
    reference_id: int | None
    reference_type: str | None
    quantity: Decimal
    balance_after: Decimal
    transaction_date: datetime

    class Config:
        from_attributes = True


class CurrentStockResponse(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    warehouse_id: int
    warehouse_name: str
    current_stock: Decimal
