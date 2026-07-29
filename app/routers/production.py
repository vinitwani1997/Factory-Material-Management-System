"""
Production ("Stock - Production") -- Raw material use karke product banana.

Ek hi request mein 2 kaam hote hain:
1. Raw material ka stock kam hota hai (PRODUCTION_CONSUME)
2. Product ka stock badhta hai (PRODUCTION_ADD)

Agar raw material kam pada, to poori request reject ho jaati hai -- kuch save
nahi hota (safety check).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import TransactionType, StockTransaction, Item
from app.schemas import ProductionCreate, TransactionOut
from app.stock_helper import get_item_or_404, record_transaction

router = APIRouter(prefix="/production", tags=["Stock - Production"])


@router.post("/")
def create_production(payload: ProductionCreate, db: Session = Depends(get_db)):
    raw_item = get_item_or_404(db, payload.raw_item_id)
    product_item = get_item_or_404(db, payload.product_item_id)

    if raw_item.item_type != "raw_material":
        raise HTTPException(status_code=400, detail=f"'{raw_item.name}' is not a raw material item")
    if product_item.item_type != "product":
        raise HTTPException(status_code=400, detail=f"'{product_item.name}' is not a product item")

    note = f"Produced '{product_item.name}' using '{raw_item.name}'"

    # 1. Raw material consume (yahi step stock check bhi karega -- kam hone par error)
    consume_txn = record_transaction(
        db=db,
        item=raw_item,
        txn_type=TransactionType.PRODUCTION_CONSUME,
        quantity=payload.raw_qty_consumed,
        remarks=payload.remarks,
        reference_note=note,
    )

    # 2. Product add
    produce_txn = record_transaction(
        db=db,
        item=product_item,
        txn_type=TransactionType.PRODUCTION_ADD,
        quantity=payload.product_qty_produced,
        remarks=payload.remarks,
        reference_note=note,
    )

    db.commit()
    db.refresh(consume_txn)
    db.refresh(produce_txn)
    db.refresh(raw_item)
    db.refresh(product_item)

    return {
        "message": "Production recorded successfully",
        "raw_material_consumed": {
            "item": raw_item.name,
            "quantity": payload.raw_qty_consumed,
            "remaining_stock": raw_item.current_stock,
        },
        "product_produced": {
            "item": product_item.name,
            "quantity": payload.product_qty_produced,
            "new_stock": product_item.current_stock,
        },
    }


@router.get("/", response_model=List[TransactionOut])
def list_production(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(
        StockTransaction.txn_type.in_(
            [TransactionType.PRODUCTION_CONSUME, TransactionType.PRODUCTION_ADD]
        )
    )
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return query.order_by(StockTransaction.id.desc()).all()
