"""
Return Material -- Jab pehle bahar gaya maal wapas aata hai (customer return,
production floor se leftover wapas, etc.), yahan entry hoti hai. Stock badh jaata hai.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import TransactionType, StockTransaction
from app.schemas import ReturnMaterialCreate, TransactionOut
from app.stock_helper import get_item_or_404, record_transaction

router = APIRouter(prefix="/return-material", tags=["Return Material"])


@router.post("/", response_model=TransactionOut)
def create_return_material(payload: ReturnMaterialCreate, db: Session = Depends(get_db)):
    item = get_item_or_404(db, payload.item_id)

    txn = record_transaction(
        db=db,
        item=item,
        txn_type=TransactionType.RETURN_MATERIAL,
        quantity=payload.quantity,
        remarks=payload.remarks,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/", response_model=List[TransactionOut])
def list_return_material(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(
        StockTransaction.txn_type == TransactionType.RETURN_MATERIAL
    )
    if item_id:
        query = query.filter(StockTransaction.item_id == item_id)
    return query.order_by(StockTransaction.id.desc()).all()
