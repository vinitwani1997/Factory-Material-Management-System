"""
Scratch In -- Scrap/waste material jo stock mein wapas add hota hai
(jaise production floor se bacha hua material). Stock badh jaata hai.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import TransactionType, StockTransaction
from app.schemas import ScratchInCreate, TransactionOut
from app.stock_helper import get_item_or_404, record_transaction

router = APIRouter(prefix="/scratch-in", tags=["Scratch In"])


@router.post("/", response_model=TransactionOut)
def add_scratch(payload: ScratchInCreate, db: Session = Depends(get_db)):
    item = get_item_or_404(db, payload.item_id)

    txn = record_transaction(
        db=db,
        item=item,
        txn_type=TransactionType.SCRATCH_IN,
        quantity=payload.quantity,
        remarks=payload.remarks,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/", response_model=List[TransactionOut])
def list_scratch_in(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(
        StockTransaction.txn_type == TransactionType.SCRATCH_IN
    )
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return query.order_by(StockTransaction.id.desc()).all()
