from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.stock_ledger import StockLedger


def get_current_stock(db: Session, item_id: int) -> Decimal:
    last = (
        db.query(StockLedger)
        .filter(StockLedger.item_id == item_id)
        .order_by(StockLedger.id.desc())
        .first()
    )
    return last.balance_after if last else Decimal("0")


def record_stock_movement(
    db: Session,
    item_id: int,
    quantity: Decimal,
    transaction_type: str,
    note: str | None = None,
    created_by: int | None = None,
) -> StockLedger:
    current = get_current_stock(db, item_id)
    entry = StockLedger(
        item_id=item_id,
        transaction_type=transaction_type,
        quantity=quantity,
        balance_after=current + quantity,
        note=note,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()
    return entry
