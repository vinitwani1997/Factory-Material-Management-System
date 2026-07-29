"""
Common helper -- har jagah (raw material in, production, out, return) yahi
function use hoga taaki stock update karne ka logic sirf ek jagah likha jaaye.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Item, StockTransaction, TransactionType

# In / Out decide karta hai ki quantity current_stock mein add hogi ya minus
INCREASING_TYPES = {
    TransactionType.RAW_MATERIAL_IN,
    TransactionType.PRODUCTION_ADD,
    TransactionType.RETURN_MATERIAL,
    TransactionType.SCRATCH_IN,
}
DECREASING_TYPES = {
    TransactionType.PRODUCTION_CONSUME,
    TransactionType.OUT_MATERIAL,
}


def get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")
    return item


def record_transaction(
    db: Session,
    item: Item,
    txn_type: TransactionType,
    quantity: float,
    remarks: str = None,
    reference_note: str = None,
):
    """
    1. Agar transaction 'decreasing' type hai (OUT / PRODUCTION_CONSUME),
       pehle check karta hai ki itna stock available hai ya nahi.
       Agar kam hai to error raise karta hai -- kuch save nahi hota.
    2. Item.current_stock ko update karta hai (+ ya -).
    3. StockTransaction table mein ek history row add karta hai.
    """
    if txn_type in DECREASING_TYPES and item.current_stock < quantity:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Not enough stock for '{item.name}'. "
                f"Available: {item.current_stock} {item.unit}, "
                f"Requested: {quantity} {item.unit}"
            ),
        )

    if txn_type in INCREASING_TYPES:
        item.current_stock += quantity
    else:
        item.current_stock -= quantity

    txn = StockTransaction(
        item_id=item.id,
        txn_type=txn_type,
        quantity=quantity,
        remarks=remarks,
        reference_note=reference_note,
    )
    db.add(txn)
    db.add(item)
    db.flush()  # taaki isi request ke andar next check ko turant updated stock dikhe
    return txn
