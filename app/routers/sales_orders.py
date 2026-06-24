"""
API routes for Sales Orders - Module 4: Outward Management - Step 1.

Mirrors Purchase Orders. Just like a PO doesn't touch stock by itself, a
Sales Order also doesn't touch stock -- it's just "the customer wants this."
Stock is only deducted when a Dispatch Note is created against this SO
(the next module), exactly mirroring how GRN is the one that adds stock
against a PO.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.partners import Customer
from app.models.warehouse import Warehouse
from app.models.item import Item
from app.models.user import User
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderStatusUpdate,
    SOItemResponse,
)

router = APIRouter(
    prefix="/sales-orders",
    tags=["Sales Orders"],
    dependencies=[Depends(get_current_user)]
)


def _build_so_response(so: SalesOrder) -> SalesOrderResponse:
    return SalesOrderResponse(
        id=so.id,
        so_number=so.so_number,
        customer_id=so.customer_id,
        customer_name=so.customer.name,
        warehouse_id=so.warehouse_id,
        warehouse_name=so.warehouse.name,
        status=so.status,
        created_by=so.created_by,
        created_at=so.created_at,
        items=[
            SOItemResponse(
                id=soi.id,
                item_id=soi.item_id,
                item_name=soi.item.name,
                item_code=soi.item.item_code,
                ordered_qty=soi.ordered_qty,
                rate=soi.rate,
            )
            for soi in so.items
        ],
    )


@router.post("/", response_model=SalesOrderResponse, status_code=201)
def create_sales_order(
    so_in: SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(SalesOrder).filter(SalesOrder.so_number == so_in.so_number).first():
        raise HTTPException(status_code=400, detail=f"SO number '{so_in.so_number}' already exists")

    if not db.query(Customer).filter(Customer.id == so_in.customer_id).first():
        raise HTTPException(status_code=400, detail=f"Customer with id {so_in.customer_id} does not exist")

    if not db.query(Warehouse).filter(Warehouse.id == so_in.warehouse_id).first():
        raise HTTPException(status_code=400, detail=f"Warehouse with id {so_in.warehouse_id} does not exist")

    for line in so_in.items:
        if not db.query(Item).filter(Item.id == line.item_id).first():
            raise HTTPException(status_code=400, detail=f"Item with id {line.item_id} does not exist")

    new_so = SalesOrder(
        so_number=so_in.so_number,
        customer_id=so_in.customer_id,
        warehouse_id=so_in.warehouse_id,
        status="pending",
        created_by=current_user.id,
    )
    db.add(new_so)
    db.flush()

    for line in so_in.items:
        db.add(SalesOrderItem(
            so_id=new_so.id,
            item_id=line.item_id,
            ordered_qty=line.ordered_qty,
            rate=line.rate,
        ))

    db.commit()
    db.refresh(new_so)
    return _build_so_response(new_so)


@router.get("/", response_model=list[SalesOrderResponse])
def list_sales_orders(
    status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(SalesOrder).options(
        joinedload(SalesOrder.customer),
        joinedload(SalesOrder.warehouse),
        joinedload(SalesOrder.items).joinedload(SalesOrderItem.item),
    )

    if status:
        query = query.filter(SalesOrder.status == status)
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)

    orders = query.order_by(SalesOrder.id.desc()).all()
    return [_build_so_response(o) for o in orders]


@router.get("/{so_id}", response_model=SalesOrderResponse)
def get_sales_order(so_id: int, db: Session = Depends(get_db)):
    so = db.query(SalesOrder).options(
        joinedload(SalesOrder.customer),
        joinedload(SalesOrder.warehouse),
        joinedload(SalesOrder.items).joinedload(SalesOrderItem.item),
    ).filter(SalesOrder.id == so_id).first()

    if not so:
        raise HTTPException(status_code=404, detail="Sales Order not found")
    return _build_so_response(so)


@router.delete("/{so_id}", status_code=204)
def cancel_sales_order(so_id: int, db: Session = Depends(get_db)):
    """Cancels a SO by setting status to 'cancelled' instead of deleting the row."""
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sales Order not found")

    if so.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a Sales Order that is already completed")

    so.status = "cancelled"
    db.commit()
    return None
