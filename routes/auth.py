from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2.id_token import verify_oauth2_token
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.users import User
from schemas.auth import (
    ForgotPassword,
    GoogleAuthRequest,
    LinkedInAuthRequest,
    ResetPassword,
    TokenResponse,
    UserCreate,
    UserLogin,
)
from schemas.base import BaseResponse
from services.email import EmailService
from services.email_templates import PASSWORD_RESET_OTP_BODY
from utils.auth import (
    generate_auth_response,
    generate_otp,
    hash_password,
    verify_password,
)
from utils.users import find_user_by_email
from utils.validation import (
    delete_email_verification_by_email,
    fetch_existing_otp,
)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/signup",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user, ensuring email uniqueness, and returns an authentication token along with subscription details."""

    existing_user = await find_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    # Check OTP verification for the email before allowing signup
    email_verification = await fetch_existing_otp(db, user.email)
    if not email_verification or not email_verification.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not verified"
        )

    new_user = User(email=user.email, password=hash_password(user.password))

    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        await delete_email_verification_by_email(db, user.email)
        print("✅ User created successfully!")
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

    return await generate_auth_response(db, new_user, "Signup successful.")


@router.post(
    "/login",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates a user by email and password, enforcing plan checks, and returns an authentication token along with subscription details."""
    db_user = await find_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    return await generate_auth_response(db, db_user, "Login successful.")


@router.post(
    "/forgot-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
async def forgot_password(data: ForgotPassword, db: AsyncSession = Depends(get_db)):
    """Initiates the forgot password flow by generating a time-limited OTP and sending it to the user's email."""
    user = await find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=5
    )

    try:
        await db.commit()

        email_context = {
            "email_title": "Password Reset Assistance",
            "username": user.email.split("@")[0],  # Inferred dynamic fallback
            "otp_code": otp,
            "expiry_minutes": 5,
            "fallback_text": f"Your verification code to reset your password is: {otp}. It expires in 5 minutes.",
        }

        await EmailService.send_templated_email(
            to_email=user.email,
            subject="Action Required: Reset Your Account Password",
            body_template=PASSWORD_RESET_OTP_BODY,
            context=email_context,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )

    return {"message": "OTP sent to your email"}


@router.post(
    "/reset-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    """Resets the user's password using the provided OTP."""
    user = await find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check OTP
    if user.otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP"
        )

    # Check expiry
    if (
        not user.otp_expiry
        or datetime.now(timezone.utc).replace(tzinfo=None) > user.otp_expiry
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired"
        )

    # Update password
    user.password = hash_password(data.new_password)

    # Clear OTP
    user.otp = None
    user.otp_expiry = None

    await db.commit()

    return {"message": "Password reset successful"}


@router.post(
    "/auth/google",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def google_authentication(
    payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    """Receives the Google ID token from the frontend, validates it against Google's token verification API, and delegates user provisioning to the shared authentication layer."""
    if not payload.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google ID token in request payload.",
        )
    try:
        id_info = verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = id_info.get("email")
        f_name = id_info.get("given_name")
        l_name = id_info.get("family_name")
        avatar = id_info.get("picture")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token payload invalid.",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credentials: {str(e)}",
        )

    return await handle_oauth_user_provisioning(
        db, email, first_name=f_name, last_name=l_name, social_avatar_url=avatar
    )


@router.post(
    "/auth/linkedin",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def linkedin_authentication(
    payload: LinkedInAuthRequest, db: AsyncSession = Depends(get_db)
):
    """
    Receives the LinkedIn access_token from the frontend, validates it against
    LinkedIn's UserInfo API, and delegates user provisioning to the shared authentication layer.
    """
    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing LinkedIn access token.",
        )
    try:
        headers = {"Authorization": f"Bearer {payload.access_token}"}
        response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify token with LinkedIn or token has expired.",
            )

        user_info = response.json()
        email = user_info.get("email")
        f_name = user_info.get("given_name")
        l_name = user_info.get("family_name")
        avatar = user_info.get("picture")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn profile missing verified email address.",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"LinkedIn authentication failed: {str(e)}",
        )

    return await handle_oauth_user_provisioning(
        db, email, first_name=f_name, last_name=l_name, social_avatar_url=avatar
    )


async def handle_oauth_user_provisioning(
    db: AsyncSession,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    social_avatar_url: Optional[str] = None,
) -> BaseResponse[TokenResponse]:
    """
    Resolves an OAuth user by email, handles fallback delta properties,
    and provisions profiles with unified social media image URLs.
    """
    user = await find_user_by_email(db, email)

    if not user:
        user = User(
            id=str(uuid4()),
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_image=social_avatar_url,
            password=None,
            otp=None,
            otp_expiry=None,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.profile_image and social_avatar_url:
            user.profile_image = social_avatar_url
            user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

    return await generate_auth_response(db, user, "Login successful.")
