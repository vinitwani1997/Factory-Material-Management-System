"""
Importing all models here so that when Base.metadata.create_all() is called
in main.py, SQLAlchemy knows about every table and creates them all.
"""

from app.models.user import Role, User, UserLocation
from app.models.warehouse import Warehouse
from app.models.item import Item
from app.models.partners import Supplier, Customer
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.grn import GRN, GRNItem
from app.models.stock_ledger import StockLedger
from app.models.bom import BOM, BOMItem
from app.models.production import ProductionOrder, MaterialIssue, FinishedGoodsReceipt, WastageRecord
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.dispatch import DispatchNote, DispatchItem

__all__ = [
    "Role",
    "User",
    "UserLocation",
    "Warehouse",
    "Item",
    "Supplier",
    "Customer",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "GRN",
    "GRNItem",
    "StockLedger",
    "BOM",
    "BOMItem",
    "ProductionOrder",
    "MaterialIssue",
    "FinishedGoodsReceipt",
    "WastageRecord",
    "SalesOrder",
    "SalesOrderItem",
    "DispatchNote",
    "DispatchItem",
]
