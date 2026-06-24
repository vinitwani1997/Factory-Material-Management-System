"""
Pydantic schemas for Module 5: Reports & Dashboard.
"""

from pydantic import BaseModel
from decimal import Decimal


class StockSummaryRow(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    category: str
    unit: str
    warehouse_id: int
    warehouse_name: str
    current_stock: Decimal
    min_stock_level: Decimal
    is_low_stock: bool
    average_rate: Decimal
    stock_value: Decimal  # current_stock * average_rate


class LowStockAlertRow(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    unit: str
    warehouse_id: int
    warehouse_name: str
    current_stock: Decimal
    min_stock_level: Decimal
    shortfall: Decimal  # how much below the minimum (min_stock_level - current_stock)


class StockValuationSummary(BaseModel):
    total_items_in_stock: int        # number of distinct item+warehouse combinations with stock > 0
    total_stock_value: Decimal       # sum of (current_stock * average_rate) across everything
    by_warehouse: list["WarehouseValuationRow"]


class WarehouseValuationRow(BaseModel):
    warehouse_id: int
    warehouse_name: str
    stock_value: Decimal


StockValuationSummary.model_rebuild()


class ItemConsumptionRow(BaseModel):
    """How much of an item was consumed (via production issue + dispatch) in a date range."""
    item_id: int
    item_code: str
    item_name: str
    unit: str
    total_consumed: Decimal  # sum of all OUT movements (production issue + dispatch + wastage), as a positive number


class SupplierPurchaseRow(BaseModel):
    """How much was purchased from a supplier (based on accepted GRN quantities)."""
    supplier_id: int
    supplier_name: str
    total_grns: int
    total_accepted_qty: Decimal
