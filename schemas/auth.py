from pydantic import BaseModel, EmailStr, Field

from schemas.subscription import UserPlanData
from schemas.users import UserProfile


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    message: str


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class GoogleAuthRequest(BaseModel):
    """Request payload for Google login."""

    id_token: str = Field(
        ..., description="The cryptographically signed ID token from NextAuth/Auth.js"
    )

    class Config:
        json_schema_extra = {
            "example": {"id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImU0N..."}
        }


class LinkedInAuthRequest(BaseModel):
    """Request payload for LinkedIn login."""

    access_token: str = Field(
        ...,
        description="The access token returned by NextAuth/Auth.js from the LinkedIn provider",
    )

    class Config:
        json_schema_extra = {"example": {"access_token": "AQX4_abc123XYZ..."}}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
    subscription: UserPlanData
