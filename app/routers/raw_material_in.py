"""
Raw Material In -- Jab factory mein kacha maal (raw material) physically aata hai,
yahan entry hoti hai. Isse item.current_stock badh jaata hai.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import TransactionType, StockTransaction
from app.schemas import RawMaterialInCreate, TransactionOut
from app.stock_helper import get_item_or_404, record_transaction

router = APIRouter(prefix="/raw-material-in", tags=["Raw Material In"])


@router.post("/", response_model=TransactionOut)
def add_raw_material(payload: RawMaterialInCreate, db: Session = Depends(get_db)):
    item = get_item_or_404(db, payload.item_id)

    txn = record_transaction(
        db=db,
        item=item,
        txn_type=TransactionType.RAW_MATERIAL_IN,
        quantity=payload.quantity,
        remarks=payload.remarks,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/", response_model=List[TransactionOut])
def list_raw_material_in(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(
        StockTransaction.txn_type == TransactionType.RAW_MATERIAL_IN
    )
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return query.order_by(StockTransaction.id.desc()).all()
