"""
Dashboard Summary -- Dashboard ke top stat cards ke liye ek hi API call mein
saare totals nikal deta hai.

Definitions (assumption -- agar isse alag chahiye ho to bata dena):
- total_scratch_in : Ab tak total kitna Scratch In hua hai (sum of quantity)
- total_items_in   : Raw Material In + Return Material + Scratch In ka total
                      (yani bahar se / wapas se andar aaya total maal)
- total_items_out  : Out Material ka total (bahar gaya maal)
- available_stock  : Abhi factory mein total kitna stock pada hai
                      (sabhi items ka current_stock jod ke)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models import Item, StockTransaction, TransactionType
from app.schemas import DashboardSummaryOut

router = APIRouter(prefix="/dashboard-summary", tags=["Dashboard"])


def _sum_qty(db: Session, txn_types) -> float:
    result = (
        db.query(func.coalesce(func.sum(StockTransaction.quantity), 0))
        .filter(StockTransaction.txn_type.in_(txn_types))
        .scalar()
    )
    return float(result or 0)


@router.get("/", response_model=DashboardSummaryOut)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_scratch_in = _sum_qty(db, [TransactionType.SCRATCH_IN])

    total_items_in = _sum_qty(
        db,
        [
            TransactionType.RAW_MATERIAL_IN,
            TransactionType.RETURN_MATERIAL,
            TransactionType.SCRATCH_IN,
        ],
    )

    total_items_out = _sum_qty(db, [TransactionType.OUT_MATERIAL])

    available_stock = float(
        db.query(func.coalesce(func.sum(Item.current_stock), 0)).scalar() or 0
    )

    return DashboardSummaryOut(
        total_scratch_in=total_scratch_in,
        total_items_in=total_items_in,
        total_items_out=total_items_out,
        available_stock=available_stock,
    )
