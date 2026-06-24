"""
API routes for Supplier Master.

Endpoints:
  POST   /suppliers/         -> create a new supplier
  GET    /suppliers/         -> list all suppliers (supports ?search=)
  GET    /suppliers/{id}     -> get one supplier
  PUT    /suppliers/{id}     -> update a supplier
  DELETE /suppliers/{id}     -> delete a supplier
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.partners import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter(
    prefix="/suppliers",
    tags=["Supplier Master"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=SupplierResponse, status_code=201)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = Supplier(**supplier.model_dump())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.get("/", response_model=list[SupplierResponse])
def list_suppliers(
    search: Optional[str] = Query(None, description="Search by supplier name"),
    db: Session = Depends(get_db)
):
    query = db.query(Supplier)
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))
    return query.order_by(Supplier.id).all()


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, supplier_update: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = supplier_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    db.commit()
    return None
