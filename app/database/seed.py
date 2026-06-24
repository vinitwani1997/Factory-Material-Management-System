"""
Seeds default roles into the database if they don't already exist.
Called once when the app starts (see main.py).

Why this is needed: User.role_id is a foreign key to roles.id, so at least
one role must exist before anyone can register.
"""

from sqlalchemy.orm import Session
from app.models.user import Role

DEFAULT_ROLES = ["Admin", "Store Manager", "Production Manager", "Operator", "Accountant"]


def seed_default_roles(db: Session):
    for role_name in DEFAULT_ROLES:
        existing = db.query(Role).filter(Role.name == role_name).first()
        if not existing:
            db.add(Role(name=role_name))
    db.commit()
