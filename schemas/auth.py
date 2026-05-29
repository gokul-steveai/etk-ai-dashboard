from pydantic import EmailStr, Field

from schemas.base import BaseSchema
from schemas.subscription import UserPlanData
from schemas.users import UserProfile


class EmailSchema(BaseSchema):
    """Reusable email schema."""

    email: EmailStr = Field(
        ...,
        description="Registered user email address",
        examples=["joe@gmail.com"],
    )


class AuthSchema(EmailSchema):
    """Base authentication schema."""

    password: str = Field(
        ...,
        min_length=8,
        description="User account password",
        examples=["StrongPassword@123"],
    )


class UserCreate(AuthSchema):
    """Schema for user registration."""

    pass


class UserLogin(AuthSchema):
    """Schema for user login."""

    pass


class ForgotPassword(EmailSchema):
    """Schema for forgot password request."""

    pass


class ResetPassword(EmailSchema):
    """Schema for password reset."""

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="OTP sent to the user's email",
        examples=["123456"],
    )

    new_password: str = Field(
        ...,
        min_length=8,
        description="New account password",
        examples=["NewStrongPassword@123"],
    )


class GoogleAuthRequest(BaseSchema):
    """Schema for Google authentication."""

    id_token: str = Field(
        ...,
        alias="id_token",
        description="Google OAuth ID token",
        examples=["eyJhbGciOiJSUzI1NiIsImtpZCI6ImU0N..."],
    )


class LinkedInAuthRequest(BaseSchema):
    """Schema for LinkedIn authentication."""

    access_token: str = Field(
        ...,
        alias="access_token",
        description="LinkedIn OAuth access token",
        examples=["AQX4_abc123XYZ..."],
    )


class BaseTokenResponse(BaseSchema):
    """Reusable token response schema."""

    access_token: str = Field(
        ...,
        description="JWT access token",
    )

    token_type: str = Field(
        default="bearer",
        description="Authentication token type",
    )


class Token(BaseTokenResponse):
    """Basic authentication response."""

    message: str = Field(
        ...,
        description="Authentication response message",
    )


class TokenResponse(BaseTokenResponse):
    """Detailed authentication response."""

    user: UserProfile = Field(
        ...,
        description="Authenticated user profile",
    )

    subscription: UserPlanData = Field(
        ...,
        description="Active subscription details",
    )
