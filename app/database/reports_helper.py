"""
Helper functions for Module 5 reports.

These are kept separate from the router (app/routers/reports.py) so the
calculation logic is easy to test/reuse independently of the HTTP layer.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.models.item import Item
from app.models.warehouse import Warehouse
from app.models.stock_ledger import StockLedger
from app.models.grn import GRN, GRNItem
from app.models.purchase_order import PurchaseOrder


def get_all_item_warehouse_balances(db: Session) -> list[dict]:
    """
    Returns the current stock balance for every (item, warehouse) combination
    that has ANY transaction history, by taking the most recent balance_after
    per group. This is the foundation for stock summary, low stock alerts,
    and valuation -- all of them start from this same balance list.
    """
    # For each item_id + warehouse_id, find the id of the most recent ledger row
    latest_ids_subquery = (
        db.query(
            StockLedger.item_id,
            StockLedger.warehouse_id,
            func.max(StockLedger.id).label("latest_id"),
        )
        .group_by(StockLedger.item_id, StockLedger.warehouse_id)
        .subquery()
    )

    latest_entries = (
        db.query(StockLedger)
        .join(
            latest_ids_subquery,
            StockLedger.id == latest_ids_subquery.c.latest_id,
        )
        .all()
    )

    return [
        {"item_id": e.item_id, "warehouse_id": e.warehouse_id, "current_stock": e.balance_after}
        for e in latest_entries
    ]


def get_average_rate(db: Session, item_id: int) -> Decimal:
    """
    Calculates the weighted average purchase rate for an item, based on all
    GRN line items for that item across all GRNs (accepted_qty * rate, summed,
    divided by total accepted_qty). The rate comes from the linked Purchase
    Order's line item for the same item.

    Returns 0 if the item has never been received via any GRN (e.g. a
    finished good that only ever comes from production, never purchased).
    """
    from app.models.purchase_order import PurchaseOrderItem

    rows = (
        db.query(GRNItem.accepted_qty, PurchaseOrderItem.rate)
        .join(GRN, GRN.id == GRNItem.grn_id)
        .join(PurchaseOrder, PurchaseOrder.id == GRN.po_id)
        .join(
            PurchaseOrderItem,
            (PurchaseOrderItem.po_id == PurchaseOrder.id) & (PurchaseOrderItem.item_id == GRNItem.item_id),
        )
        .filter(GRNItem.item_id == item_id)
        .all()
    )

    total_qty = sum((r.accepted_qty for r in rows), Decimal("0"))
    if total_qty == 0:
        return Decimal("0")

    total_value = sum((r.accepted_qty * r.rate for r in rows), Decimal("0"))
    return total_value / total_qty
