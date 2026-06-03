from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String

from core.database import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    email = Column(String(255), primary_key=True, index=True)
    otp = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
