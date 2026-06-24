"""
API route to list available item categories.

INTENTIONALLY left WITHOUT authentication, same reasoning as /roles/ --
this is static reference data (not user data), used to populate a dropdown
when creating/editing an item. Kept as its own router (separate from
/items/) because the items router has authentication applied at the
router level to ALL its routes -- keeping this separate avoids needing
a route-specific exception there.

Endpoints:
  GET /item-categories/   -> list all valid item categories (value + label)
"""

from fastapi import APIRouter

from app.constants import ITEM_CATEGORIES
from app.schemas.item_category import ItemCategoryResponse

router = APIRouter(
    prefix="/item-categories",
    tags=["Item Categories"]
)


@router.get("/", response_model=list[ItemCategoryResponse])
def list_item_categories():
    return ITEM_CATEGORIES
