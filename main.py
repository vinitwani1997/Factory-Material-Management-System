"""
FMMS Backend - Main Application Entry Point

To run this project:
    1. python -m venv venv
    2. source venv/bin/activate        (Windows: venv\\Scripts\\activate)
    3. pip install -r requirements.txt
    4. uvicorn main:app --reload

Then open: http://127.0.0.1:8000/docs
This gives you an interactive API tester (Swagger UI) - no Postman needed
to get started.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import Base, engine, SessionLocal
from app.models import *  # noqa: F401, F403 - imports all models so tables get created
from app.database.seed import seed_default_roles
from app.routers import items, auth, warehouses, suppliers, customers, roles, purchase_orders, item_categories, grn, stock, bom, production_orders, sales_orders, dispatch, reports

# Create all tables in SQLite if they don't already exist.
# NOTE: In production, this should be replaced by a proper migration tool (Alembic),
# but for development with SQLite this is the fastest way to get started.
Base.metadata.create_all(bind=engine)

# Seed default roles (Admin, Store Manager, etc.) so registration works immediately.
_seed_db = SessionLocal()
seed_default_roles(_seed_db)
_seed_db.close()

app = FastAPI(
    title="Factory Material Management System (FMMS)",
    description="Backend API for tracking raw material, production, and finished goods for a manufacturing unit.",
    version="0.1.0"
)

# Allow the React frontend (running on a different port) to call this API.
# "*" is fine for local development. Restrict this to your actual frontend
# domain before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (more will be added as we build more modules)
app.include_router(roles.router)
app.include_router(item_categories.router)
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(warehouses.router)
app.include_router(suppliers.router)
app.include_router(customers.router)
app.include_router(purchase_orders.router)
app.include_router(grn.router)
app.include_router(stock.router)
app.include_router(bom.router)
app.include_router(production_orders.router)
app.include_router(sales_orders.router)
app.include_router(dispatch.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"message": "FMMS Backend is running", "docs": "/docs"}
