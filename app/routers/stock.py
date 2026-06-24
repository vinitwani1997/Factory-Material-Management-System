"""
Read-only API routes for viewing stock movement history and current stock.

NOTE: This is a minimal version for now. Full reporting (stock summary
across all items/warehouses, low stock alerts, stock valuation) is part of
Module 5 and will be built out later. For now this gives just enough to
verify that GRN entries are actually updating stock correctly.

Endpoints:
  GET /stock/ledger          -> raw transaction history (supports ?item_id= and ?warehouse_id=)
  GET /stock/current         -> current stock balance for one item at one warehouse
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.stock_helper import get_current_stock
from app.models.stock_ledger import StockLedger
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.stock_ledger import StockLedgerEntryResponse, CurrentStockResponse

router = APIRouter(
    prefix="/stock",
    tags=["Stock Ledger"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/ledger", response_model=list[StockLedgerEntryResponse])
def view_stock_ledger(
    item_id: int | None = Query(None),
    warehouse_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(StockLedger).options(
        joinedload(StockLedger.item),
        joinedload(StockLedger.warehouse),
    )

    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    if warehouse_id:
        query = query.filter(StockLedger.warehouse_id == warehouse_id)

    entries = query.order_by(StockLedger.id.desc()).all()

    return [
        StockLedgerEntryResponse(
            id=e.id,
            item_id=e.item_id,
            item_name=e.item.name,
            item_code=e.item.item_code,
            warehouse_id=e.warehouse_id,
            warehouse_name=e.warehouse.name,
            transaction_type=e.transaction_type,
            reference_id=e.reference_id,
            reference_type=e.reference_type,
            quantity=e.quantity,
            balance_after=e.balance_after,
            transaction_date=e.transaction_date,
        )
        for e in entries
    ]


@router.get("/current", response_model=CurrentStockResponse)
def view_current_stock(
    item_id: int = Query(..., description="Item id to check"),
    warehouse_id: int = Query(..., description="Warehouse id to check"),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    balance = get_current_stock(db, item_id, warehouse_id)

    return CurrentStockResponse(
        item_id=item.id,
        item_name=item.name,
        item_code=item.item_code,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        current_stock=balance,
    )
