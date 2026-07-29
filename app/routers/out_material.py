"""
Out Material -- Jab koi maal (raw material ya product) factory se bahar jaata hai
(sale, dispatch, transfer, etc.), yahan entry hoti hai. Stock kam ho jaata hai.

Agar available stock se zyada nikalne ki koshish ki, to request reject ho jaati hai.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import TransactionType, StockTransaction
from app.schemas import OutMaterialCreate, TransactionOut
from app.stock_helper import get_item_or_404, record_transaction

router = APIRouter(prefix="/out-material", tags=["Out Material"])


@router.post("/", response_model=TransactionOut)
def create_out_material(payload: OutMaterialCreate, db: Session = Depends(get_db)):
    item = get_item_or_404(db, payload.item_id)

    txn = record_transaction(
        db=db,
        item=item,
        txn_type=TransactionType.OUT_MATERIAL,
        quantity=payload.quantity,
        remarks=payload.remarks,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/", response_model=List[TransactionOut])
def list_out_material(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(
        StockTransaction.txn_type == TransactionType.OUT_MATERIAL
    )
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return query.order_by(StockTransaction.id.desc()).all()
