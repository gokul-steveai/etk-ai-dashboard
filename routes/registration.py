from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.auth import OTPRequest, OTPVerificationRequest
from schemas.base import BaseResponse
from utils.auth import generate_otp, send_email
from utils.users import find_user_by_email
from utils.validation import (
    fetch_existing_otp,
    is_email_otp_valid,
    save_or_update_email_verification_otp,
    update_email_verification_status,
)

router = APIRouter(prefix="/registration", tags=["Registration"])


@router.post(
    "/generate-otp", response_model=BaseResponse[None], status_code=status.HTTP_200_OK
)
async def request_otp(data: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Generates and sends an OTP to the provided email for registration purposes."""

    existing_user = await find_user_by_email(db, data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    otp = generate_otp()

    if send_email(
        to_email=data.email, subject="OTP for Registration", body=f"Your OTP is: {otp}"
    ):
        await save_or_update_email_verification_otp(db, data.email, otp)

        return BaseResponse(
            success=True,
            message="OTP sent successfully. Please check your email.",
            data=None,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again later.",
        )


# Verify OTP endpoint
@router.post(
    "/verify-otp", response_model=BaseResponse[None], status_code=status.HTTP_200_OK
)
async def verify_otp(data: OTPVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Verifies the provided OTP for the given email and returns a success message if valid."""

    is_valid_otp = await is_email_otp_valid(db, data.email, data.otp)
    if is_valid_otp:
        await update_email_verification_status(db, data.email, is_verified=True)
        return BaseResponse(
            success=True, message="OTP verified successfully.", data=None
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
        )
