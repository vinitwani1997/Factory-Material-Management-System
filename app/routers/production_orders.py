"""
API routes for Production Orders - Module 3: Production - Step 2.

Endpoints:
  POST   /production-orders/                -> create a new production order (status: planned)
  GET    /production-orders/                -> list all (supports ?status= and ?warehouse_id=)
  GET    /production-orders/{id}            -> get one with full material issue / FG receipt / wastage details
  PATCH  /production-orders/{id}/status     -> update status to in_progress / cancelled
  POST   /production-orders/{id}/complete   -> complete the order -- THIS is what moves stock

What happens when a production order is completed (POST .../complete):
  1. Validate the order isn't already completed or cancelled.
  2. Look up the BOM linked to this order to know the raw material recipe.
  3. For each raw material in the BOM: required_qty = bom_qty_required * actual_qty produced.
     - Check there's enough stock available; if not, reject the whole request
       (nothing is saved -- the production floor needs to know BEFORE they
       report completion, not after stock goes negative).
     - Record a stock movement (PRODUCTION_ISSUE, negative) for each raw material.
  4. Record any wastage entries provided (these also deduct from stock, since
     wasted material was still consumed, just didn't end up in the finished product).
  5. Record a stock movement (FG_RECEIPT, positive) for the finished item,
     quantity = actual_qty.
  6. Mark the order "completed".

All of this happens in a single transaction -- if step 3's stock check fails
for ANY raw material, nothing at all is saved.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from decimal import Decimal

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.database.stock_helper import record_stock_movement, get_current_stock
from app.models.production import ProductionOrder, MaterialIssue, FinishedGoodsReceipt, WastageRecord
from app.models.bom import BOM
from app.models.warehouse import Warehouse
from app.models.item import Item
from app.models.user import User
from app.schemas.production import (
    ProductionOrderCreate,
    ProductionOrderResponse,
    ProductionOrderStatusUpdate,
    ProductionOrderComplete,
    MaterialIssueResponse,
    FGReceiptResponse,
    WastageResponse,
)

router = APIRouter(
    prefix="/production-orders",
    tags=["Production Orders"],
    dependencies=[Depends(get_current_user)]
)


def _build_response(po: ProductionOrder) -> ProductionOrderResponse:
    return ProductionOrderResponse(
        id=po.id,
        order_number=po.order_number,
        bom_id=po.bom_id,
        finished_item_id=po.bom.finished_item_id,
        finished_item_name=po.bom.finished_item.name,
        warehouse_id=po.warehouse_id,
        warehouse_name=po.warehouse.name,
        planned_qty=po.planned_qty,
        actual_qty=po.actual_qty,
        status=po.status,
        start_date=po.start_date,
        end_date=po.end_date,
        created_by=po.created_by,
        created_at=po.created_at,
        material_issues=[
            MaterialIssueResponse(
                item_id=mi.item_id, item_name=mi.item.name, item_code=mi.item.item_code, issued_qty=mi.issued_qty
            )
            for mi in po.material_issues
        ],
        fg_receipts=[
            FGReceiptResponse(
                item_id=fg.item_id, item_name=fg.item.name, item_code=fg.item.item_code, received_qty=fg.received_qty
            )
            for fg in po.fg_receipts
        ],
        wastage_records=[
            WastageResponse(
                item_id=w.item_id, item_name=w.item.name, item_code=w.item.item_code,
                wasted_qty=w.wasted_qty, reason=w.reason
            )
            for w in po.wastage_records
        ],
    )


def _get_loaded_order(db: Session, order_id: int) -> ProductionOrder:
    order = db.query(ProductionOrder).options(
        joinedload(ProductionOrder.bom).joinedload(BOM.finished_item),
        joinedload(ProductionOrder.bom).joinedload(BOM.bom_items),
        joinedload(ProductionOrder.warehouse),
        joinedload(ProductionOrder.material_issues),
        joinedload(ProductionOrder.fg_receipts),
        joinedload(ProductionOrder.wastage_records),
    ).filter(ProductionOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Production Order not found")
    return order


@router.post("/", response_model=ProductionOrderResponse, status_code=201)
def create_production_order(
    order_in: ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(ProductionOrder).filter(ProductionOrder.order_number == order_in.order_number).first():
        raise HTTPException(status_code=400, detail=f"Order number '{order_in.order_number}' already exists")

    bom = db.query(BOM).filter(BOM.id == order_in.bom_id).first()
    if not bom:
        raise HTTPException(status_code=400, detail=f"BOM with id {order_in.bom_id} does not exist")
    if not bom.is_active:
        raise HTTPException(status_code=400, detail="This BOM is not active. Use the currently active BOM for this finished item.")

    if not db.query(Warehouse).filter(Warehouse.id == order_in.warehouse_id).first():
        raise HTTPException(status_code=400, detail=f"Warehouse with id {order_in.warehouse_id} does not exist")

    new_order = ProductionOrder(
        order_number=order_in.order_number,
        bom_id=order_in.bom_id,
        warehouse_id=order_in.warehouse_id,
        planned_qty=order_in.planned_qty,
        status="planned",
        start_date=order_in.start_date,
        created_by=current_user.id,
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return _build_response(_get_loaded_order(db, new_order.id))


@router.get("/", response_model=list[ProductionOrderResponse])
def list_production_orders(
    status: Optional[str] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ProductionOrder).options(
        joinedload(ProductionOrder.bom).joinedload(BOM.finished_item),
        joinedload(ProductionOrder.bom).joinedload(BOM.bom_items),
        joinedload(ProductionOrder.warehouse),
        joinedload(ProductionOrder.material_issues),
        joinedload(ProductionOrder.fg_receipts),
        joinedload(ProductionOrder.wastage_records),
    )

    if status:
        query = query.filter(ProductionOrder.status == status)
    if warehouse_id:
        query = query.filter(ProductionOrder.warehouse_id == warehouse_id)

    orders = query.order_by(ProductionOrder.id.desc()).all()
    return [_build_response(o) for o in orders]


@router.get("/{order_id}", response_model=ProductionOrderResponse)
def get_production_order(order_id: int, db: Session = Depends(get_db)):
    return _build_response(_get_loaded_order(db, order_id))


@router.patch("/{order_id}/status", response_model=ProductionOrderResponse)
def update_status(order_id: int, status_update: ProductionOrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production Order not found")

    if order.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot change status of a {order.status} order")

    order.status = status_update.status
    db.commit()
    return _build_response(_get_loaded_order(db, order_id))


@router.post("/{order_id}/complete", response_model=ProductionOrderResponse)
def complete_production_order(
    order_id: int,
    completion: ProductionOrderComplete,
    db: Session = Depends(get_db),
):
    order = _get_loaded_order(db, order_id)

    if order.status == "completed":
        raise HTTPException(status_code=400, detail="This production order is already completed")
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot complete a cancelled production order")

    bom = order.bom

    # ---- Step 1: Calculate raw material requirements and validate stock availability ----
    # required_qty for each raw material = bom's qty_required (per 1 unit) * actual_qty produced
    requirements: dict[int, Decimal] = {}
    for bom_item in bom.bom_items:
        requirements[bom_item.raw_item_id] = bom_item.qty_required * completion.actual_qty

    # Add any wastage on top of the BOM requirement -- wasted material was
    # also consumed from stock, it just didn't make it into the finished product.
    for w in completion.wastage:
        requirements[w.item_id] = requirements.get(w.item_id, Decimal("0")) + w.wasted_qty

    # Check stock availability BEFORE making any changes. If any item is short,
    # reject the whole request -- nothing should be saved.
    shortages = []
    for item_id, required_qty in requirements.items():
        available = get_current_stock(db, item_id, order.warehouse_id)
        if available < required_qty:
            item = db.query(Item).filter(Item.id == item_id).first()
            shortages.append(
                f"{item.name if item else f'Item #{item_id}'}: need {required_qty}, only {available} available"
            )

    if shortages:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock to complete this production order: {'; '.join(shortages)}"
        )

    # ---- Step 2: Issue raw materials (deduct stock) per the BOM ----
    for bom_item in bom.bom_items:
        qty_to_issue = bom_item.qty_required * completion.actual_qty
        db.add(MaterialIssue(
            production_order_id=order.id,
            item_id=bom_item.raw_item_id,
            issued_qty=qty_to_issue,
        ))
        record_stock_movement(
            db,
            item_id=bom_item.raw_item_id,
            warehouse_id=order.warehouse_id,
            quantity=-qty_to_issue,  # negative: stock going OUT
            transaction_type="PRODUCTION_ISSUE",
            reference_id=order.id,
            reference_type="PRODUCTION_ORDER",
        )

    # ---- Step 3: Record wastage (also deducts stock) ----
    for w in completion.wastage:
        db.add(WastageRecord(
            production_order_id=order.id,
            item_id=w.item_id,
            wasted_qty=w.wasted_qty,
            reason=w.reason,
        ))
        record_stock_movement(
            db,
            item_id=w.item_id,
            warehouse_id=order.warehouse_id,
            quantity=-w.wasted_qty,  # negative: stock going OUT
            transaction_type="WASTAGE",
            reference_id=order.id,
            reference_type="PRODUCTION_ORDER",
        )

    # ---- Step 4: Receive finished goods (add stock) ----
    db.add(FinishedGoodsReceipt(
        production_order_id=order.id,
        item_id=bom.finished_item_id,
        received_qty=completion.actual_qty,
    ))
    record_stock_movement(
        db,
        item_id=bom.finished_item_id,
        warehouse_id=order.warehouse_id,
        quantity=completion.actual_qty,  # positive: stock coming IN
        transaction_type="FG_RECEIPT",
        reference_id=order.id,
        reference_type="PRODUCTION_ORDER",
    )

    # ---- Step 5: Mark the order completed ----
    order.actual_qty = completion.actual_qty
    order.status = "completed"
    if completion.end_date:
        order.end_date = completion.end_date

    db.commit()
    return _build_response(_get_loaded_order(db, order_id))
