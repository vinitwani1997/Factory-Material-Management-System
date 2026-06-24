from pydantic import BaseModel, Field


class WarehouseCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["Plant A - MIDC Nashik"])
    address: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    is_active: bool | None = None


class WarehouseResponse(BaseModel):
    id: int
    name: str
    address: str | None
    is_active: bool

    class Config:
        from_attributes = True
