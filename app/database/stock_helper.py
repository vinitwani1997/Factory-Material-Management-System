"""
Reusable stock ledger helper.

Any module that moves stock (GRN, production issue, finished goods receipt,
dispatch, stock transfer, wastage) should call `record_stock_movement()`
instead of writing to stock_ledger directly. This keeps the balance
calculation logic in ONE place.
"""

from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.stock_ledger import StockLedger


def get_current_stock(db: Session, item_id: int, warehouse_id: int) -> Decimal:
    """
    Returns the current stock balance for an item at a specific warehouse,
    by reading the most recent stock_ledger entry's balance_after.
    Returns 0 if there is no stock history yet.
    """
    last_entry = (
        db.query(StockLedger)
        .filter(StockLedger.item_id == item_id, StockLedger.warehouse_id == warehouse_id)
        .order_by(StockLedger.id.desc())
        .first()
    )
    return last_entry.balance_after if last_entry else Decimal("0")


def record_stock_movement(
    db: Session,
    item_id: int,
    warehouse_id: int,
    quantity: Decimal,
    transaction_type: str,
    reference_id: int | None = None,
    reference_type: str | None = None,
) -> StockLedger:
    """
    Records one stock movement and returns the created ledger row.

    `quantity` should be POSITIVE for stock coming IN (e.g. GRN_IN, FG_RECEIPT)
    and NEGATIVE for stock going OUT (e.g. PRODUCTION_ISSUE, DISPATCH_OUT, WASTAGE).

    NOTE: This function adds the row to the session but does NOT commit --
    the calling endpoint is responsible for db.commit(), so that the stock
    entry and whatever triggered it (e.g. the GRN) are saved together as a
    single all-or-nothing transaction.
    """
    current_balance = get_current_stock(db, item_id, warehouse_id)
    new_balance = current_balance + quantity

    entry = StockLedger(
        item_id=item_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        reference_id=reference_id,
        reference_type=reference_type,
        quantity=quantity,
        balance_after=new_balance,
    )
    db.add(entry)

    # IMPORTANT: flush (not commit) immediately so that if record_stock_movement()
    # is called AGAIN within the same request (e.g. production completion issues
    # multiple raw materials, then records wastage, all in one transaction),
    # get_current_stock()'s database query sees this entry and calculates the
    # next balance correctly. Without this flush, get_current_stock() would
    # keep reading the OLD balance for every call within the same transaction,
    # silently producing wrong running balances when multiple movements happen
    # for the same item+warehouse before the final commit.
    db.flush()

    return entry
