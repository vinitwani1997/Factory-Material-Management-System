"""
Pydantic schemas for authentication: register, token, and user response.

NOTE: There is no "UserLogin" schema here -- the /auth/login endpoint uses
FastAPI's built-in OAuth2PasswordRequestForm instead (form-data, not JSON),
so that Swagger's "Authorize" button works correctly. See app/routers/auth.py
for details and a React fetch() example.
"""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Fields needed to create a new user. Used by Admin to add employees."""
    name: str = Field(..., max_length=100, examples=["Rahul Sharma"])
    email: EmailStr
    password: str = Field(..., min_length=6, examples=["secret123"])
    role_id: int = Field(..., examples=[1])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True
