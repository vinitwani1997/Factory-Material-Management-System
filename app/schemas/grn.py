"""
Pydantic schemas for GRN (Goods Receipt Note).

Like Purchase Orders, a GRN is created with its line items in a SINGLE
request: the GRN header (which PO, which warehouse, received date) plus
a list of line items, each recording received/accepted/rejected quantities.
"""

from pydantic import BaseModel, Field, model_validator
from decimal import Decimal
from datetime import date, datetime


# ---- Line item schemas ----

class GRNItemCreate(BaseModel):
    """One line item within a GRN creation request."""
    item_id: int
    received_qty: Decimal = Field(..., gt=0, description="Total quantity physically received")
    accepted_qty: Decimal = Field(..., ge=0, description="Quantity that passed quality check")
    rejected_qty: Decimal = Field(default=0, ge=0, description="Quantity that failed quality check")
    batch_number: str | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def check_quantities_add_up(self):
        if self.accepted_qty + self.rejected_qty != self.received_qty:
            raise ValueError(
                f"accepted_qty ({self.accepted_qty}) + rejected_qty ({self.rejected_qty}) "
                f"must equal received_qty ({self.received_qty})"
            )
        return self


class GRNItemResponse(BaseModel):
    id: int
    item_id: int
    item_name: str
    item_code: str
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    batch_number: str | None

    class Config:
        from_attributes = True


# ---- GRN schemas ----

class GRNCreate(BaseModel):
    grn_number: str = Field(..., max_length=50, examples=["GRN-2026-001"])
    po_id: int
    received_date: date
    items: list[GRNItemCreate] = Field(..., min_length=1, description="At least one item is required")


class GRNResponse(BaseModel):
    id: int
    grn_number: str
    po_id: int
    po_number: str
    warehouse_id: int
    warehouse_name: str
    received_date: date
    created_by: int
    created_at: datetime
    items: list[GRNItemResponse]

    class Config:
        from_attributes = True
