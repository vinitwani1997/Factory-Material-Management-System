"""
API routes for Warehouse Master (plants / godowns / locations).

Endpoints:
  POST   /warehouses/         -> create a new warehouse
  GET    /warehouses/         -> list all warehouses
  GET    /warehouses/{id}     -> get one warehouse
  PUT    /warehouses/{id}     -> update a warehouse
  DELETE /warehouses/{id}     -> deactivate a warehouse (soft delete, see note below)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.deps import get_current_user
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate, WarehouseResponse

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouse Master"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=WarehouseResponse, status_code=201)
def create_warehouse(warehouse: WarehouseCreate, db: Session = Depends(get_db)):
    new_warehouse = Warehouse(**warehouse.model_dump())
    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)
    return new_warehouse


@router.get("/", response_model=list[WarehouseResponse])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).order_by(Warehouse.id).all()


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: int, warehouse_update: WarehouseUpdate, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    update_data = warehouse_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(warehouse, field, value)

    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}", status_code=204)
def deactivate_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    """
    NOTE: This is a soft delete (just marks is_active = False) instead of
    actually removing the row. We do this because warehouses are referenced
    by purchase orders, stock ledger entries, etc. -- deleting the row would
    break historical records. The same approach should be used later for
    items, suppliers, and customers once they have transactions linked to them.
    """
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    warehouse.is_active = False
    db.commit()
    return None
