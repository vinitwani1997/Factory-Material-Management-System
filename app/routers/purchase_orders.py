"""
API routes for Purchase Orders (Module 2: Inward Management - Step 1).

Endpoints:
  POST   /purchase-orders/          -> create a new PO with its line items (single request)
  GET    /purchase-orders/          -> list all POs (supports ?status= and ?supplier_id=)
  GET    /purchase-orders/{id}      -> get one PO with full item details
  PATCH  /purchase-orders/{id}/status -> update PO status (pending/partial/completed/cancelled)
  DELETE /purchase-orders/{id}      -> cancel a PO (soft delete via status, not a real delete)

NOTE: A PO is only the "we ordered this" record. It does NOT touch stock.
Stock only changes later when a GRN (goods receipt) is created against this PO --
that's the next module we build.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.partners import Supplier
from app.models.warehouse import Warehouse
from app.models.item import Item
from app.models.user import User
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderStatusUpdate,
    POItemResponse,
)

router = APIRouter(
    prefix="/purchase-orders",
    tags=["Purchase Orders"],
    dependencies=[Depends(get_current_user)]
)


def _build_po_response(po: PurchaseOrder) -> PurchaseOrderResponse:
    """
    Converts a PurchaseOrder ORM object into the response schema, manually
    filling in supplier_name / warehouse_name / item_name / item_code so the
    frontend doesn't need to make extra API calls just to display the PO.
    """
    return PurchaseOrderResponse(
        id=po.id,
        po_number=po.po_number,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name,
        warehouse_id=po.warehouse_id,
        warehouse_name=po.warehouse.name,
        status=po.status,
        created_by=po.created_by,
        created_at=po.created_at,
        items=[
            POItemResponse(
                id=poi.id,
                item_id=poi.item_id,
                item_name=poi.item.name,
                item_code=poi.item.item_code,
                ordered_qty=poi.ordered_qty,
                rate=poi.rate,
            )
            for poi in po.items
        ],
    )


@router.post("/", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order(
    po_in: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate po_number is unique
    if db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_in.po_number).first():
        raise HTTPException(status_code=400, detail=f"PO number '{po_in.po_number}' already exists")

    # Validate supplier exists
    if not db.query(Supplier).filter(Supplier.id == po_in.supplier_id).first():
        raise HTTPException(status_code=400, detail=f"Supplier with id {po_in.supplier_id} does not exist")

    # Validate warehouse exists
    if not db.query(Warehouse).filter(Warehouse.id == po_in.warehouse_id).first():
        raise HTTPException(status_code=400, detail=f"Warehouse with id {po_in.warehouse_id} does not exist")

    # Validate every item_id in the list actually exists
    for line in po_in.items:
        if not db.query(Item).filter(Item.id == line.item_id).first():
            raise HTTPException(status_code=400, detail=f"Item with id {line.item_id} does not exist")

    # Create the PO header
    new_po = PurchaseOrder(
        po_number=po_in.po_number,
        supplier_id=po_in.supplier_id,
        warehouse_id=po_in.warehouse_id,
        status="pending",
        created_by=current_user.id,
    )
    db.add(new_po)
    db.flush()  # generates new_po.id without fully committing yet, so we can attach items to it

    # Create each line item, linked to this PO
    for line in po_in.items:
        db.add(PurchaseOrderItem(
            po_id=new_po.id,
            item_id=line.item_id,
            ordered_qty=line.ordered_qty,
            rate=line.rate,
        ))

    db.commit()
    db.refresh(new_po)
    return _build_po_response(new_po)


@router.get("/", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(
    status: Optional[str] = Query(None, description="Filter by pending/partial/completed/cancelled"),
    supplier_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.warehouse),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.item),
    )

    if status:
        query = query.filter(PurchaseOrder.status == status)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)

    pos = query.order_by(PurchaseOrder.id.desc()).all()
    return [_build_po_response(po) for po in pos]


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.warehouse),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.item),
    ).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return _build_po_response(po)


@router.patch("/{po_id}/status", response_model=PurchaseOrderResponse)
def update_po_status(po_id: int, status_update: PurchaseOrderStatusUpdate, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    po.status = status_update.status
    db.commit()
    db.refresh(po)
    return _build_po_response(po)


@router.delete("/{po_id}", status_code=204)
def cancel_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """
    Cancels a PO by setting its status to 'cancelled' instead of deleting the
    row. We never hard-delete a PO once created, because GRNs may reference it
    later, and historical records should always be traceable.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    if po.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a PO that is already completed")

    po.status = "cancelled"
    db.commit()
    return None
