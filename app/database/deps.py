"""
Dependency used to protect routes.

Usage in any router:
    from app.database.deps import get_current_user

    @router.get("/something")
    def my_route(current_user: User = Depends(get_current_user)):
        ...

If the request has no valid token, FastAPI automatically returns 401
before your route code even runs.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.security import decode_access_token
from app.models.user import User

# tokenUrl just tells Swagger UI which endpoint issues tokens (for the "Authorize" button)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    return user


def require_role(*allowed_role_names: str):
    """
    Optional helper for role-based access control.
    Example usage:
        @router.delete("/items/{id}")
        def delete_item(current_user: User = Depends(require_role("Admin"))):
            ...
    Only users whose role name is in allowed_role_names can access the route.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_role_names)}"
            )
        return current_user
    return role_checker
