"""
Available Material -- Ye batata hai ki ABHI factory mein kya-kya, kitna pada hai.
Read-only report hai, kuch change nahi karta.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import Item
from app.schemas import AvailableMaterialOut

router = APIRouter(prefix="/available-material", tags=["Available Material"])


@router.get("/", response_model=List[AvailableMaterialOut])
def get_available_material(
    item_type: Optional[str] = None,
    only_in_stock: bool = True,
    db: Session = Depends(get_db),
):
    """
    - item_type: 'raw_material' ya 'product' se filter kar sakte ho
    - only_in_stock: default True -- sirf wahi items dikhata hai jinka stock 0 se zyada hai
    """
    query = db.query(Item)
    if item_type:
        query = query.filter(Item.item_type == item_type)
    if only_in_stock:
        query = query.filter(Item.current_stock > 0)

    items = query.order_by(Item.name).all()

    return [
        AvailableMaterialOut(
            item_id=item.id,
            name=item.name,
            item_type=item.item_type,
            unit=item.unit,
            current_stock=item.current_stock,
        )
        for item in items
    ]


@router.get("/{item_id}", response_model=AvailableMaterialOut)
def get_available_material_by_item(item_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return AvailableMaterialOut(
        item_id=item.id,
        name=item.name,
        item_type=item.item_type,
        unit=item.unit,
        current_stock=item.current_stock,
    )
