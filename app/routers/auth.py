"""
Authentication APIs.

Endpoints:
  POST /auth/register  -> create a new user (normally restricted to Admin in production)
  POST /auth/login      -> verify email+password, return a JWT token
  GET  /auth/me         -> return the currently logged-in user's details (token required)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.security import hash_password, verify_password, create_access_token
from app.database.deps import get_current_user
from app.models.user import User, Role
from app.schemas.auth import UserRegister, TokenResponse, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Check email isn't already used
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    # Check the role_id actually exists
    role = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role with id {user_in.role_id} does not exist")

    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role_id=user_in.role_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Uses OAuth2PasswordRequestForm (form-data, not JSON) instead of a plain
    Pydantic schema. This is what FastAPI's Swagger "Authorize" button sends
    by default, so login works seamlessly from the /docs page.

    IMPORTANT for the React frontend: this means the login request must be
    sent as `application/x-www-form-urlencoded` (form-data), NOT JSON.
    The "username" field should contain the user's email.

    Example using fetch in React:
        const body = new URLSearchParams();
        body.append('username', email);   // yes, 'username' even though it's an email
        body.append('password', password);
        fetch('/auth/login', { method: 'POST', body });
    """
    # form_data.username holds the email (OAuth2 spec calls it "username" by convention)
    user = db.query(User).filter(User.email == form_data.username).first()

    # Deliberately vague error message - don't reveal whether the email exists or not
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    token = create_access_token(data={"user_id": user.id, "email": user.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user
