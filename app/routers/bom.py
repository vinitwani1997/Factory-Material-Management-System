"""
API routes for BOM (Bill of Materials) - Module 3: Production - Step 1.

Endpoints:
  POST   /boms/          -> create a new BOM (recipe) for a finished item
  GET    /boms/          -> list all BOMs (supports ?finished_item_id=)
  GET    /boms/{id}      -> get one BOM with full raw material breakdown
  PATCH  /boms/{id}/deactivate -> deactivate a BOM (e.g. when a new version replaces it)

NOTE: When creating a new BOM for a finished_item_id that already has an
active BOM, the old one is automatically deactivated -- only one BOM should
be active per finished item at a time, since that's what Production Orders
will use to calculate raw material requirements.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.bom import BOM, BOMItem
from app.models.item import Item
from app.schemas.bom import BOMCreate, BOMResponse, BOMItemResponse

router = APIRouter(
    prefix="/boms",
    tags=["BOM (Bill of Materials)"],
    dependencies=[Depends(get_current_user)]
)


def _build_bom_response(bom: BOM) -> BOMResponse:
    return BOMResponse(
        id=bom.id,
        finished_item_id=bom.finished_item_id,
        finished_item_name=bom.finished_item.name,
        finished_item_code=bom.finished_item.item_code,
        version=bom.version,
        is_active=bom.is_active,
        bom_items=[
            BOMItemResponse(
                id=bi.id,
                raw_item_id=bi.raw_item_id,
                raw_item_name=bi.raw_item.name,
                raw_item_code=bi.raw_item.item_code,
                unit=bi.raw_item.unit,
                qty_required=bi.qty_required,
            )
            for bi in bom.bom_items
        ],
    )


@router.post("/", response_model=BOMResponse, status_code=201)
def create_bom(bom_in: BOMCreate, db: Session = Depends(get_db)):
    # Validate the finished item exists
    finished_item = db.query(Item).filter(Item.id == bom_in.finished_item_id).first()
    if not finished_item:
        raise HTTPException(status_code=400, detail=f"Item with id {bom_in.finished_item_id} does not exist")

    # Validate every raw material item exists
    for line in bom_in.bom_items:
        if not db.query(Item).filter(Item.id == line.raw_item_id).first():
            raise HTTPException(status_code=400, detail=f"Raw material item with id {line.raw_item_id} does not exist")

    # A finished item can't be its own raw material
    raw_ids = {line.raw_item_id for line in bom_in.bom_items}
    if bom_in.finished_item_id in raw_ids:
        raise HTTPException(status_code=400, detail="A finished item cannot be listed as its own raw material")

    # Deactivate any existing active BOM for this finished item -- only one active version at a time
    db.query(BOM).filter(
        BOM.finished_item_id == bom_in.finished_item_id,
        BOM.is_active == True,  # noqa: E712
    ).update({"is_active": False})

    new_bom = BOM(
        finished_item_id=bom_in.finished_item_id,
        version=bom_in.version,
        is_active=True,
    )
    db.add(new_bom)
    db.flush()

    for line in bom_in.bom_items:
        db.add(BOMItem(
            bom_id=new_bom.id,
            raw_item_id=line.raw_item_id,
            qty_required=line.qty_required,
        ))

    db.commit()
    db.refresh(new_bom)
    return _build_bom_response(new_bom)


@router.get("/", response_model=list[BOMResponse])
def list_boms(
    finished_item_id: Optional[int] = Query(None),
    active_only: bool = Query(True, description="If true (default), only show currently active BOMs"),
    db: Session = Depends(get_db),
):
    query = db.query(BOM).options(
        joinedload(BOM.finished_item),
        joinedload(BOM.bom_items).joinedload(BOMItem.raw_item),
    )

    if finished_item_id:
        query = query.filter(BOM.finished_item_id == finished_item_id)
    if active_only:
        query = query.filter(BOM.is_active == True)  # noqa: E712

    boms = query.order_by(BOM.id.desc()).all()
    return [_build_bom_response(b) for b in boms]


@router.get("/{bom_id}", response_model=BOMResponse)
def get_bom(bom_id: int, db: Session = Depends(get_db)):
    bom = db.query(BOM).options(
        joinedload(BOM.finished_item),
        joinedload(BOM.bom_items).joinedload(BOMItem.raw_item),
    ).filter(BOM.id == bom_id).first()

    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    return _build_bom_response(bom)


@router.patch("/{bom_id}/deactivate", response_model=BOMResponse)
def deactivate_bom(bom_id: int, db: Session = Depends(get_db)):
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")

    bom.is_active = False
    db.commit()
    db.refresh(bom)
    return _build_bom_response(bom)
