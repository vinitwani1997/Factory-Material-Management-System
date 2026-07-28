from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.stock_helper import record_stock_movement, get_current_stock
from app.models.item import Item
from app.models.stock_ledger import StockLedger
from app.models.user import User
from app.schemas.stock import (
    StockInCreate,
    ProductionCreate,
    StockOutCreate,
    ReturnCreate,
    StockLedgerResponse,
    AvailableStockRow,
)

router = APIRouter(
    prefix="/stock",
    tags=["Stock"],
    dependencies=[Depends(get_current_user)]
)


def _get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")
    return item


# ── 1. Raw Material IN ────────────────────────────────────────────────────────

@router.post("/in", response_model=StockLedgerResponse, status_code=201)
def stock_in(
    data: StockInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Raw material received / purchased — adds to stock."""
    item = _get_item_or_404(db, data.item_id)
    if item.category != "raw_material":
        raise HTTPException(status_code=400, detail="Stock IN is only for raw materials")

    entry = record_stock_movement(
        db, item_id=data.item_id, quantity=data.quantity,
        transaction_type="STOCK_IN", note=data.note, created_by=current_user.id,
    )
    db.commit()
    db.refresh(entry)
    return entry


# ── 2. Production ─────────────────────────────────────────────────────────────

@router.post("/production", response_model=list[StockLedgerResponse], status_code=201)
def production(
    data: ProductionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Use raw material → make product.
    Deducts raw_qty_used from raw material stock.
    Adds product_qty_made to product stock.
    """
    raw_item = _get_item_or_404(db, data.raw_material_id)
    product_item = _get_item_or_404(db, data.product_id)

    if raw_item.category != "raw_material":
        raise HTTPException(status_code=400, detail="raw_material_id must be a raw material item")
    if product_item.category != "product":
        raise HTTPException(status_code=400, detail="product_id must be a product item")

    available = get_current_stock(db, data.raw_material_id)
    if available < data.raw_qty_used:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: need {data.raw_qty_used} {raw_item.unit}, only {available} available"
        )

    note = data.note or f"Production: {data.raw_qty_used} {raw_item.unit} → {data.product_qty_made} {product_item.unit}"

    raw_entry = record_stock_movement(
        db, item_id=data.raw_material_id, quantity=-data.raw_qty_used,
        transaction_type="PRODUCTION_ISSUE", note=note, created_by=current_user.id,
    )
    product_entry = record_stock_movement(
        db, item_id=data.product_id, quantity=data.product_qty_made,
        transaction_type="PRODUCTION_RECEIPT", note=note, created_by=current_user.id,
    )

    db.commit()
    db.refresh(raw_entry)
    db.refresh(product_entry)
    return [raw_entry, product_entry]


# ── 3. Material OUT ───────────────────────────────────────────────────────────

@router.post("/out", response_model=StockLedgerResponse, status_code=201)
def stock_out(
    data: StockOutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Material dispatched / sent out — deducts from stock."""
    item = _get_item_or_404(db, data.item_id)

    available = get_current_stock(db, data.item_id)
    if available < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: need {data.quantity} {item.unit}, only {available} available"
        )

    entry = record_stock_movement(
        db, item_id=data.item_id, quantity=-data.quantity,
        transaction_type="STOCK_OUT", note=data.note, created_by=current_user.id,
    )
    db.commit()
    db.refresh(entry)
    return entry


# ── 4. Return Material ────────────────────────────────────────────────────────

@router.post("/return", response_model=StockLedgerResponse, status_code=201)
def return_material(
    data: ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return material:
    - return_from_customer → product coming back IN (adds to stock)
    - return_to_supplier   → raw material going back OUT (deducts from stock)
    """
    item = _get_item_or_404(db, data.item_id)

    if data.return_type == "return_to_supplier":
        available = get_current_stock(db, data.item_id)
        if available < data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock to return: need {data.quantity} {item.unit}, only {available} available"
            )
        qty = -data.quantity  # going OUT
    else:
        qty = data.quantity   # coming IN

    entry = record_stock_movement(
        db, item_id=data.item_id, quantity=qty,
        transaction_type=data.return_type.upper(), note=data.note, created_by=current_user.id,
    )
    db.commit()
    db.refresh(entry)
    return entry


# ── 5. Available Stock ────────────────────────────────────────────────────────

@router.get("/available", response_model=list[AvailableStockRow])
def available_stock(
    category: Optional[str] = Query(None, description="raw_material or product"),
    db: Session = Depends(get_db),
):
    """Current stock balance for every item."""
    items = db.query(Item)
    if category:
        items = items.filter(Item.category == category)
    items = items.order_by(Item.id).all()

    rows = []
    for item in items:
        current = get_current_stock(db, item.id)
        rows.append(AvailableStockRow(
            item_id=item.id,
            item_code=item.item_code,
            item_name=item.name,
            category=item.category,
            unit=item.unit,
            current_stock=current,
            min_stock_level=item.min_stock_level,
            is_low_stock=current < item.min_stock_level,
        ))
    return rows


# ── 6. Ledger History ─────────────────────────────────────────────────────────

@router.get("/ledger", response_model=list[StockLedgerResponse])
def ledger(
    item_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Full transaction history, optionally filtered by item or type."""
    query = db.query(StockLedger)
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    if transaction_type:
        query = query.filter(StockLedger.transaction_type == transaction_type)
    return query.order_by(StockLedger.id.desc()).all()
