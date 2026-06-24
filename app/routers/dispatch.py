"""
API routes for Dispatch Notes - Module 4: Outward Management - Step 2.

Endpoints:
  POST   /dispatch/          -> create a dispatch against a SO; this is what
                                 actually deducts stock
  GET    /dispatch/          -> list all dispatches (supports ?so_id=)
  GET    /dispatch/{id}      -> get one dispatch with full item details

What happens when a Dispatch Note is created:
  1. Validate the SO exists and is not cancelled/already completed.
  2. Validate every item_id in the dispatch actually belongs to that SO.
  3. Check stock availability for every item FIRST -- if any item doesn't
     have enough stock, reject the entire request (nothing saved). This
     mirrors the same safety check used in production order completion.
  4. Create the dispatch header + line items.
  5. Record a stock movement (DISPATCH_OUT, negative) for each item.
  6. Re-check the SO: if total dispatched quantity across all dispatch notes
     >= ordered quantity for every line item, mark the SO "completed";
     otherwise "partial".
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from decimal import Decimal

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.stock_helper import record_stock_movement, get_current_stock
from app.models.dispatch import DispatchNote, DispatchItem
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.item import Item
from app.models.user import User
from app.schemas.dispatch import DispatchNoteCreate, DispatchNoteResponse, DispatchItemResponse

router = APIRouter(
    prefix="/dispatch",
    tags=["Dispatch Notes"],
    dependencies=[Depends(get_current_user)]
)


def _build_dispatch_response(dispatch: DispatchNote) -> DispatchNoteResponse:
    return DispatchNoteResponse(
        id=dispatch.id,
        dispatch_number=dispatch.dispatch_number,
        so_id=dispatch.so_id,
        so_number=dispatch.sales_order.so_number,
        warehouse_id=dispatch.warehouse_id,
        warehouse_name=dispatch.warehouse.name,
        dispatch_date=dispatch.dispatch_date,
        vehicle_number=dispatch.vehicle_number,
        driver_name=dispatch.driver_name,
        created_by=dispatch.created_by,
        created_at=dispatch.created_at,
        items=[
            DispatchItemResponse(
                id=di.id,
                item_id=di.item_id,
                item_name=di.item.name,
                item_code=di.item.item_code,
                dispatched_qty=di.dispatched_qty,
            )
            for di in dispatch.items
        ],
    )


def _refresh_so_status(db: Session, so: SalesOrder):
    """Same logic as PO status refresh in grn.py, mirrored for the outward side."""
    all_fulfilled = True

    for so_item in so.items:
        total_dispatched = (
            db.query(func.coalesce(func.sum(DispatchItem.dispatched_qty), 0))
            .join(DispatchNote, DispatchNote.id == DispatchItem.dispatch_id)
            .filter(DispatchNote.so_id == so.id, DispatchItem.item_id == so_item.item_id)
            .scalar()
        )
        if Decimal(total_dispatched) < so_item.ordered_qty:
            all_fulfilled = False
            break

    so.status = "completed" if all_fulfilled else "partial"


@router.post("/", response_model=DispatchNoteResponse, status_code=201)
def create_dispatch(
    dispatch_in: DispatchNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(DispatchNote).filter(DispatchNote.dispatch_number == dispatch_in.dispatch_number).first():
        raise HTTPException(status_code=400, detail=f"Dispatch number '{dispatch_in.dispatch_number}' already exists")

    so = db.query(SalesOrder).options(joinedload(SalesOrder.items)).filter(
        SalesOrder.id == dispatch_in.so_id
    ).first()
    if not so:
        raise HTTPException(status_code=400, detail=f"Sales Order with id {dispatch_in.so_id} does not exist")

    if so.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot dispatch against a cancelled Sales Order")
    if so.status == "completed":
        raise HTTPException(status_code=400, detail="This Sales Order is already fully completed")

    so_item_ids = {soi.item_id for soi in so.items}
    for line in dispatch_in.items:
        if line.item_id not in so_item_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Item id {line.item_id} is not part of Sales Order {so.so_number}"
            )

    # Check stock availability for every item BEFORE making any changes.
    shortages = []
    for line in dispatch_in.items:
        available = get_current_stock(db, line.item_id, so.warehouse_id)
        if available < line.dispatched_qty:
            item = db.query(Item).filter(Item.id == line.item_id).first()
            shortages.append(
                f"{item.name if item else f'Item #{line.item_id}'}: need {line.dispatched_qty}, only {available} available"
            )

    if shortages:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock to dispatch: {'; '.join(shortages)}"
        )

    # Create the dispatch header (warehouse comes from the SO)
    new_dispatch = DispatchNote(
        dispatch_number=dispatch_in.dispatch_number,
        so_id=so.id,
        warehouse_id=so.warehouse_id,
        dispatch_date=dispatch_in.dispatch_date,
        vehicle_number=dispatch_in.vehicle_number,
        driver_name=dispatch_in.driver_name,
        created_by=current_user.id,
    )
    db.add(new_dispatch)
    db.flush()

    for line in dispatch_in.items:
        db.add(DispatchItem(
            dispatch_id=new_dispatch.id,
            item_id=line.item_id,
            dispatched_qty=line.dispatched_qty,
        ))
        record_stock_movement(
            db,
            item_id=line.item_id,
            warehouse_id=so.warehouse_id,
            quantity=-line.dispatched_qty,  # negative: stock going OUT
            transaction_type="DISPATCH_OUT",
            reference_id=new_dispatch.id,
            reference_type="DISPATCH",
        )

    db.flush()
    _refresh_so_status(db, so)

    db.commit()
    db.refresh(new_dispatch)
    return _build_dispatch_response(new_dispatch)


@router.get("/", response_model=list[DispatchNoteResponse])
def list_dispatches(
    so_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(DispatchNote).options(
        joinedload(DispatchNote.sales_order),
        joinedload(DispatchNote.warehouse),
        joinedload(DispatchNote.items).joinedload(DispatchItem.item),
    )

    if so_id:
        query = query.filter(DispatchNote.so_id == so_id)

    dispatches = query.order_by(DispatchNote.id.desc()).all()
    return [_build_dispatch_response(d) for d in dispatches]


@router.get("/{dispatch_id}", response_model=DispatchNoteResponse)
def get_dispatch(dispatch_id: int, db: Session = Depends(get_db)):
    dispatch = db.query(DispatchNote).options(
        joinedload(DispatchNote.sales_order),
        joinedload(DispatchNote.warehouse),
        joinedload(DispatchNote.items).joinedload(DispatchItem.item),
    ).filter(DispatchNote.id == dispatch_id).first()

    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch Note not found")
    return _build_dispatch_response(dispatch)
