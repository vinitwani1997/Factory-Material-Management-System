"""
API routes for Module 5: Reports & Dashboard.

All endpoints here are read-only -- none of them change stock or any other
data. They build on top of the existing stock_ledger table.

Endpoints:
  GET /reports/stock-summary     -> current stock for every item at every warehouse, with value
  GET /reports/low-stock         -> items currently below their minimum stock level
  GET /reports/stock-valuation   -> total stock value, broken down by warehouse
  GET /reports/consumption       -> how much of each item was consumed (production + dispatch + wastage)
  GET /reports/supplier-purchases -> total accepted quantity purchased per supplier
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.reports_helper import get_all_item_warehouse_balances, get_average_rate
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.models.partners import Supplier
from app.models.stock_ledger import StockLedger
from app.models.grn import GRN, GRNItem
from app.models.purchase_order import PurchaseOrder
from app.schemas.reports import (
    StockSummaryRow,
    LowStockAlertRow,
    StockValuationSummary,
    WarehouseValuationRow,
    ItemConsumptionRow,
    SupplierPurchaseRow,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Dashboard"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/stock-summary", response_model=list[StockSummaryRow])
def stock_summary(
    warehouse_id: Optional[int] = Query(None, description="Filter to a single warehouse"),
    category: Optional[str] = Query(None, description="Filter by raw_material / semi_finished / finished_good"),
    only_in_stock: bool = Query(True, description="If true (default), hide rows where current_stock is 0"),
    db: Session = Depends(get_db),
):
    """
    Current stock for every item at every warehouse that has stock history,
    along with its average purchase rate and calculated stock value.
    """
    balances = get_all_item_warehouse_balances(db)

    items_by_id = {i.id: i for i in db.query(Item).all()}
    warehouses_by_id = {w.id: w for w in db.query(Warehouse).all()}

    rows = []
    for bal in balances:
        item = items_by_id.get(bal["item_id"])
        warehouse = warehouses_by_id.get(bal["warehouse_id"])
        if not item or not warehouse:
            continue  # shouldn't happen, but skip defensively rather than 500

        if warehouse_id and warehouse.id != warehouse_id:
            continue
        if category and item.category != category:
            continue

        current_stock = bal["current_stock"]
        if only_in_stock and current_stock <= 0:
            continue

        avg_rate = get_average_rate(db, item.id)

        rows.append(StockSummaryRow(
            item_id=item.id,
            item_code=item.item_code,
            item_name=item.name,
            category=item.category,
            unit=item.unit,
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            current_stock=current_stock,
            min_stock_level=item.min_stock_level,
            is_low_stock=current_stock < item.min_stock_level,
            average_rate=avg_rate,
            stock_value=current_stock * avg_rate,
        ))

    # Most useful items first: low stock items surfaced at the top
    rows.sort(key=lambda r: (not r.is_low_stock, r.item_name))
    return rows


@router.get("/low-stock", response_model=list[LowStockAlertRow])
def low_stock_alerts(
    warehouse_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Items currently below their min_stock_level, across all warehouses (or a specific one)."""
    balances = get_all_item_warehouse_balances(db)

    items_by_id = {i.id: i for i in db.query(Item).all()}
    warehouses_by_id = {w.id: w for w in db.query(Warehouse).all()}

    alerts = []
    for bal in balances:
        item = items_by_id.get(bal["item_id"])
        warehouse = warehouses_by_id.get(bal["warehouse_id"])
        if not item or not warehouse:
            continue

        if warehouse_id and warehouse.id != warehouse_id:
            continue

        current_stock = bal["current_stock"]
        if current_stock >= item.min_stock_level:
            continue  # not low on stock, skip

        alerts.append(LowStockAlertRow(
            item_id=item.id,
            item_code=item.item_code,
            item_name=item.name,
            unit=item.unit,
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            current_stock=current_stock,
            min_stock_level=item.min_stock_level,
            shortfall=item.min_stock_level - current_stock,
        ))

    # Worst shortfall first -- most urgent items at the top
    alerts.sort(key=lambda a: -a.shortfall)
    return alerts


@router.get("/stock-valuation", response_model=StockValuationSummary)
def stock_valuation(db: Session = Depends(get_db)):
    """
    Total stock value across the whole factory, broken down by warehouse.
    Uses weighted average purchase rate (across all GRNs) for each item.
    """
    balances = get_all_item_warehouse_balances(db)
    items_by_id = {i.id: i for i in db.query(Item).all()}
    warehouses_by_id = {w.id: w for w in db.query(Warehouse).all()}

    value_by_warehouse: dict[int, Decimal] = {}
    total_value = Decimal("0")
    items_in_stock = 0

    for bal in balances:
        current_stock = bal["current_stock"]
        if current_stock <= 0:
            continue

        item = items_by_id.get(bal["item_id"])
        warehouse = warehouses_by_id.get(bal["warehouse_id"])
        if not item or not warehouse:
            continue

        avg_rate = get_average_rate(db, item.id)
        value = current_stock * avg_rate

        total_value += value
        items_in_stock += 1
        value_by_warehouse[warehouse.id] = value_by_warehouse.get(warehouse.id, Decimal("0")) + value

    by_warehouse = [
        WarehouseValuationRow(
            warehouse_id=wid,
            warehouse_name=warehouses_by_id[wid].name,
            stock_value=val,
        )
        for wid, val in value_by_warehouse.items()
    ]
    by_warehouse.sort(key=lambda r: -r.stock_value)

    return StockValuationSummary(
        total_items_in_stock=items_in_stock,
        total_stock_value=total_value,
        by_warehouse=by_warehouse,
    )


@router.get("/consumption", response_model=list[ItemConsumptionRow])
def item_consumption(
    warehouse_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Total quantity consumed per item -- sum of all OUTGOING stock movements
    (PRODUCTION_ISSUE, DISPATCH_OUT, WASTAGE), shown as a positive number.
    """
    query = (
        db.query(
            StockLedger.item_id,
            func.sum(-StockLedger.quantity).label("total_consumed"),
        )
        .filter(StockLedger.transaction_type.in_(["PRODUCTION_ISSUE", "DISPATCH_OUT", "WASTAGE"]))
    )

    if warehouse_id:
        query = query.filter(StockLedger.warehouse_id == warehouse_id)

    results = query.group_by(StockLedger.item_id).all()

    items_by_id = {i.id: i for i in db.query(Item).all()}

    rows = []
    for item_id, total_consumed in results:
        item = items_by_id.get(item_id)
        if not item:
            continue
        rows.append(ItemConsumptionRow(
            item_id=item.id,
            item_code=item.item_code,
            item_name=item.name,
            unit=item.unit,
            total_consumed=total_consumed,
        ))

    rows.sort(key=lambda r: -r.total_consumed)
    return rows


@router.get("/supplier-purchases", response_model=list[SupplierPurchaseRow])
def supplier_purchases(db: Session = Depends(get_db)):
    """Total accepted quantity received per supplier, across all their GRNs."""
    results = (
        db.query(
            PurchaseOrder.supplier_id,
            func.count(func.distinct(GRN.id)).label("total_grns"),
            func.sum(GRNItem.accepted_qty).label("total_accepted_qty"),
        )
        .join(GRN, GRN.po_id == PurchaseOrder.id)
        .join(GRNItem, GRNItem.grn_id == GRN.id)
        .group_by(PurchaseOrder.supplier_id)
        .all()
    )

    suppliers_by_id = {s.id: s for s in db.query(Supplier).all()}

    rows = []
    for supplier_id, total_grns, total_accepted_qty in results:
        supplier = suppliers_by_id.get(supplier_id)
        if not supplier:
            continue
        rows.append(SupplierPurchaseRow(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            total_grns=total_grns,
            total_accepted_qty=total_accepted_qty or Decimal("0"),
        ))

    rows.sort(key=lambda r: -r.total_accepted_qty)
    return rows
