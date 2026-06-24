"""
Security utilities: password hashing and JWT token creation/verification.

IMPORTANT: SECRET_KEY below is a placeholder for development only.
Before deploying to production, move this to an environment variable
and generate a strong random key, e.g.:
    python -c "import secrets; print(secrets.token_hex(32))"
"""

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

# ---- Password hashing setup ----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Converts a plain text password into a secure hash before storing in DB."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks a login attempt's password against the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---- JWT settings ----
SECRET_KEY = "CHANGE-THIS-TO-A-RANDOM-SECRET-KEY-BEFORE-PRODUCTION"  # TODO: move to .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours - a typical work shift


def create_access_token(data: dict) -> str:
    """
    Creates a signed JWT token containing the given data (usually user id, email, role).
    The frontend stores this token and sends it back in the Authorization header
    on every subsequent request: "Authorization: Bearer <token>"
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Verifies a token's signature and expiry. Returns the payload, or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
