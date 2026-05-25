from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CHAR, Column, DateTime, String
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    __tablename__ = "users2"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    profile_image = Column(String(255), nullable=True)
    otp = Column(String(10), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, default=None)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    subscription = relationship(
        "UserSubscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
