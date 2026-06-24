from pydantic import BaseModel, Field, EmailStr


class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=150, examples=["Bajaj Auto Ltd"])
    contact_number: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    gst_number: str | None = Field(None, max_length=20)
    address: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    contact_number: str | None = None
    email: EmailStr | None = None
    gst_number: str | None = None
    address: str | None = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    contact_number: str | None
    email: str | None
    gst_number: str | None
    address: str | None

    class Config:
        from_attributes = True
