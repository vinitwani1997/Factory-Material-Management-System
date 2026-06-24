"""
API routes for Item Master (Module 1).

Endpoints:
  POST   /items/         -> create a new item
  GET    /items/         -> list all items (with optional search & category filter)
  GET    /items/{id}     -> get one item by id
  PUT    /items/{id}     -> update an item
  DELETE /items/{id}     -> delete an item
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse

router = APIRouter(
    prefix="/items",
    tags=["Item Master"],
    dependencies=[Depends(get_current_user)]  # every endpoint in this router now requires a valid login token
)


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    # Check item_code is not already used
    existing = db.query(Item).filter(Item.item_code == item.item_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Item code '{item.item_code}' already exists")

    new_item = Item(**item.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.get("/", response_model=list[ItemResponse])
def list_items(
    category: Optional[str] = Query(None, description="Filter by raw_material / semi_finished / finished_good"),
    search: Optional[str] = Query(None, description="Search by item name or item code"),
    db: Session = Depends(get_db)
):
    query = db.query(Item)

    if category:
        query = query.filter(Item.category == category)

    if search:
        query = query.filter(
            or_(
                Item.name.ilike(f"%{search}%"),
                Item.item_code.ilike(f"%{search}%")
            )
        )

    return query.order_by(Item.id).all()


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = item_update.model_dump(exclude_unset=True)  # only fields actually sent
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return None
