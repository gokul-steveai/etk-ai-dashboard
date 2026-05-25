import hashlib
import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.users import User
from schemas.auth import TokenResponse
from schemas.base import BaseResponse
from schemas.users import UserProfile
from utils.users import (
    ensure_user_has_free_plan,
    find_user_by_email,
    get_user_active_plan,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current authenticated user."""
    token = credentials.credentials

    try:
        payload = verify_token(token)

        if payload is None or payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token.",
            )

        email: str = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token.",
        )

    user = await find_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found."
        )

    return user


# JWT token creation
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# JWT token verification
def verify_token(token: str) -> dict | None:
    """
    Verifies a JWT token and returns the payload if valid, otherwise returns None.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def preprocess_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str):
    password = preprocess_password(password)
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    plain = preprocess_password(plain)
    return pwd_context.verify(plain, hashed)


# Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))


# Send Email
def send_email(to_email, otp):
    subject = "Password Reset OTP"
    body = f"Your OTP is: {otp}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
        server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email error:", e)


async def generate_auth_response(
    db: AsyncSession, user: User, message: str
) -> BaseResponse[TokenResponse]:
    """
    Unified utility to handle plan enforcement, token generation,
    and packaging the standard authenticated user JSON structure.
    """
    await ensure_user_has_free_plan(db, str(user.id))

    access_token = create_access_token({"sub": user.email, "user_id": str(user.id)})

    subscription_data = await get_user_active_plan(db, str(user.id))

    return BaseResponse(
        success=True,
        message=message,
        data=TokenResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=access_token,
            token_type="bearer",
            subscription=subscription_data,
            user=UserProfile(
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                profile_image=user.profile_image or "",
                created_at=user.created_at,
                id=str(user.id),
                email=user.email,
            ),
        ),
    )
