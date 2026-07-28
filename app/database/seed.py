from sqlalchemy.orm import Session
from app.models.user import Role

DEFAULT_ROLES = ["Admin", "Operator"]


def seed_default_roles(db: Session):
    for role_name in DEFAULT_ROLES:
        if not db.query(Role).filter(Role.name == role_name).first():
            db.add(Role(name=role_name))
    db.commit()
