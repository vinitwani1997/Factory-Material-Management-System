"""
Item Master -- Raw Material aur Product dono yahin register hote hain.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemUpdate, ItemOut

router = APIRouter(prefix="/items", tags=["Item Master"])


@router.post("/", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(
        name=payload.name,
        item_type=payload.item_type,
        unit=payload.unit,
        current_stock=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=List[ItemOut])
def list_items(
    item_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if item_type:
        query = query.filter(Item.item_type == item_type)
    if search:
        query = query.filter(Item.name.ilike(f"%{search}%"))
    return query.order_by(Item.id).all()


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.name is not None:
        item.name = payload.name
    if payload.unit is not None:
        item.unit = payload.unit

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": f"Item '{item.name}' deleted successfully"}
