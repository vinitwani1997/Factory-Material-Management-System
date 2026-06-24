"""
API route to list all available roles.

INTENTIONALLY left WITHOUT authentication, because this is needed
BEFORE a user can register/login -- the registration form needs to show
"Admin", "Store Manager", etc. as options, and at that point no token
exists yet. Role names are not sensitive data, so this is safe to leave open.

Endpoints:
  GET /roles/   -> list all roles (id + name), to be used as a dropdown
                    when registering a new user
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import Role
from app.schemas.role import RoleResponse

router = APIRouter(
    prefix="/roles",
    tags=["Roles"]
)


@router.get("/", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.id).all()
