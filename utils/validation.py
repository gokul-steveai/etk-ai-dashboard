from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.email_verification import EmailVerification


async def fetch_existing_otp(db: AsyncSession, email: str) -> EmailVerification | None:
    """Fetches the existing OTP record for the given email, if it exists."""
    response = await db.execute(
        select(EmailVerification).filter(EmailVerification.email == email)
    )
    return response.scalars().first()


async def save_or_update_email_verification_otp(
    db: AsyncSession, email: str, otp: str, expires_in_minutes: int = 5
) -> None:
    """Saves a new OTP record or updates the existing one for the given email."""
    existing_otp = await fetch_existing_otp(db, email)

    if existing_otp:
        existing_otp.otp = otp
        existing_otp.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=expires_in_minutes
        )
        existing_otp.is_verified = False
        await db.commit()

        return existing_otp
    else:
        email_verification = EmailVerification(
            email=email,
            otp=otp,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=expires_in_minutes),
        )

        db.add(email_verification)
        await db.commit()

        return email_verification


async def is_email_otp_valid(db: AsyncSession, email: str, otp: str) -> bool:
    """Checks if the provided OTP is valid for the given email."""
    email_verification = await fetch_existing_otp(db, email)
    return bool(
        email_verification
        and email_verification.otp == otp
        and email_verification.expires_at
        > datetime.now(timezone.utc).replace(tzinfo=None)
    )


async def update_email_verification_status(
    db: AsyncSession, email: str, is_verified: bool
) -> None:
    """Updates the verification status of the email in the database."""
    await db.execute(
        update(EmailVerification)
        .where(EmailVerification.email == email)
        .values(is_verified=is_verified)
    )
    await db.commit()


async def delete_email_verification_by_email(db: AsyncSession, email: str) -> None:
    """Deletes the email verification record for the given email."""
    existing_otp = await fetch_existing_otp(db, email)

    if existing_otp:
        await db.delete(existing_otp)
        await db.commit()
