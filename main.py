"""
FMMS Simple -- App entry point.
Run this with: uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import Base, engine
from app import models  # noqa: F401  -- import zaroor hai taaki tables register ho jaayein

from app.routers import (
    items,
    raw_material_in,
    production,
    out_material,
    return_material,
    available_material,
    scratch_in,
    dashboard,
)

# Sare tables (agar already nahi bane) create kar deta hai
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FMMS Simple",
    description=(
        "Simple Factory Material Management System.\n\n"
        "Modules: Item | Raw Material In | Stock (Production) | "
        "Out Material | Available Material | Return Material"
    ),
    version="1.0.0",
)

# Frontend se (React, etc.) call allow karne ke liye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(raw_material_in.router)
app.include_router(production.router)
app.include_router(out_material.router)
app.include_router(return_material.router)
app.include_router(available_material.router)
app.include_router(scratch_in.router)
app.include_router(dashboard.router)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "FMMS Simple backend is running"}
