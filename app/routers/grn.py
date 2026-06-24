"""
API routes for GRN (Goods Receipt Note) - Module 2: Inward Management - Step 2.

Endpoints:
  POST   /grn/          -> create a GRN against a PO; this is what actually
                            updates stock (only accepted_qty goes into stock_ledger)
  GET    /grn/          -> list all GRNs (supports ?po_id=)
  GET    /grn/{id}      -> get one GRN with full item details

What happens when a GRN is created:
  1. Validate the PO exists and is not cancelled/already completed.
  2. Validate every item_id in the GRN actually belongs to that PO.
  3. Create the GRN header + line items.
  4. For each line item, record a stock movement (GRN_IN) for the accepted_qty
     only -- rejected material never enters stock.
  5. Re-check the PO: if total accepted quantity across all GRNs >= ordered
     quantity for every line item, mark the PO "completed"; otherwise "partial".

All of this happens inside a single database transaction -- if anything
fails partway through, nothing is saved (db.commit() is called only once,
at the very end).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from decimal import Decimal

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.stock_helper import record_stock_movement
from app.models.grn import GRN, GRNItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.item import Item
from app.models.user import User
from app.schemas.grn import GRNCreate, GRNResponse, GRNItemResponse

router = APIRouter(
    prefix="/grn",
    tags=["GRN (Goods Receipt Note)"],
    dependencies=[Depends(get_current_user)]
)


def _build_grn_response(grn: GRN) -> GRNResponse:
    """Converts a GRN ORM object into the response schema with friendly names filled in."""
    return GRNResponse(
        id=grn.id,
        grn_number=grn.grn_number,
        po_id=grn.po_id,
        po_number=grn.purchase_order.po_number,
        warehouse_id=grn.warehouse_id,
        warehouse_name=grn.warehouse.name,
        received_date=grn.received_date,
        created_by=grn.created_by,
        created_at=grn.created_at,
        items=[
            GRNItemResponse(
                id=gi.id,
                item_id=gi.item_id,
                item_name=gi.item.name,
                item_code=gi.item.item_code,
                received_qty=gi.received_qty,
                accepted_qty=gi.accepted_qty,
                rejected_qty=gi.rejected_qty,
                batch_number=gi.batch_number,
            )
            for gi in grn.items
        ],
    )


def _refresh_po_status(db: Session, po: PurchaseOrder):
    """
    Recalculates whether a PO should be 'partial' or 'completed' based on
    total accepted quantity received so far across ALL its GRNs, compared
    to what was ordered for each line item.
    """
    all_fulfilled = True

    for po_item in po.items:
        total_accepted = (
            db.query(func.coalesce(func.sum(GRNItem.accepted_qty), 0))
            .join(GRN, GRN.id == GRNItem.grn_id)
            .filter(GRN.po_id == po.id, GRNItem.item_id == po_item.item_id)
            .scalar()
        )
        if Decimal(total_accepted) < po_item.ordered_qty:
            all_fulfilled = False
            break

    po.status = "completed" if all_fulfilled else "partial"


@router.post("/", response_model=GRNResponse, status_code=201)
def create_grn(
    grn_in: GRNCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate GRN number is unique
    if db.query(GRN).filter(GRN.grn_number == grn_in.grn_number).first():
        raise HTTPException(status_code=400, detail=f"GRN number '{grn_in.grn_number}' already exists")

    # Validate the PO exists
    po = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.items)).filter(
        PurchaseOrder.id == grn_in.po_id
    ).first()
    if not po:
        raise HTTPException(status_code=400, detail=f"Purchase Order with id {grn_in.po_id} does not exist")

    if po.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot create a GRN against a cancelled Purchase Order")
    if po.status == "completed":
        raise HTTPException(status_code=400, detail="This Purchase Order is already fully completed")

    # Validate every item in the GRN actually belongs to this PO
    po_item_ids = {poi.item_id for poi in po.items}
    for line in grn_in.items:
        if line.item_id not in po_item_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Item id {line.item_id} is not part of Purchase Order {po.po_number}"
            )

    # Create the GRN header (warehouse comes from the PO -- material is received where it was ordered to)
    new_grn = GRN(
        grn_number=grn_in.grn_number,
        po_id=po.id,
        warehouse_id=po.warehouse_id,
        received_date=grn_in.received_date,
        created_by=current_user.id,
    )
    db.add(new_grn)
    db.flush()  # generates new_grn.id so we can attach items and stock entries to it

    # Create each line item + record the stock movement for accepted quantity
    for line in grn_in.items:
        db.add(GRNItem(
            grn_id=new_grn.id,
            item_id=line.item_id,
            received_qty=line.received_qty,
            accepted_qty=line.accepted_qty,
            rejected_qty=line.rejected_qty,
            batch_number=line.batch_number,
        ))

        # Only the accepted quantity goes into stock. Rejected material is
        # recorded on the GRN for traceability but never enters stock_ledger.
        if line.accepted_qty > 0:
            record_stock_movement(
                db,
                item_id=line.item_id,
                warehouse_id=po.warehouse_id,
                quantity=line.accepted_qty,
                transaction_type="GRN_IN",
                reference_id=new_grn.id,
                reference_type="GRN",
            )

    # Recalculate PO status (partial vs completed) based on everything received so far
    db.flush()  # make sure this GRN's items are visible to the status check query below
    _refresh_po_status(db, po)

    db.commit()
    db.refresh(new_grn)
    return _build_grn_response(new_grn)


@router.get("/", response_model=list[GRNResponse])
def list_grns(
    po_id: Optional[int] = Query(None, description="Filter by Purchase Order id"),
    db: Session = Depends(get_db),
):
    query = db.query(GRN).options(
        joinedload(GRN.purchase_order),
        joinedload(GRN.warehouse),
        joinedload(GRN.items).joinedload(GRNItem.item),
    )

    if po_id:
        query = query.filter(GRN.po_id == po_id)

    grns = query.order_by(GRN.id.desc()).all()
    return [_build_grn_response(g) for g in grns]


@router.get("/{grn_id}", response_model=GRNResponse)
def get_grn(grn_id: int, db: Session = Depends(get_db)):
    grn = db.query(GRN).options(
        joinedload(GRN.purchase_order),
        joinedload(GRN.warehouse),
        joinedload(GRN.items).joinedload(GRNItem.item),
    ).filter(GRN.id == grn_id).first()

    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    return _build_grn_response(grn)
