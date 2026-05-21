import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from database import Base
from schemas import PlanName, SubscriptionStatus


class User(Base):
    __tablename__ = "users2"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
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


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = Column(CHAR(36), ForeignKey("users2.id"), unique=True, nullable=False)
    data = Column(JSON, nullable=False)

    user = relationship("User")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    name = Column(Enum(PlanName), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    max_saved_queries = Column(Integer, default=0, nullable=False)
    max_compare_countries = Column(Integer, default=2, nullable=False)

    # Subscription plan features JSON
    features = Column(JSON, nullable=False, default=dict)

    stripe_price_id = Column(String(255), unique=True, nullable=True)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = Column(CHAR(36), ForeignKey("users2.id"), unique=True, nullable=False)
    plan_id = Column(CHAR(36), ForeignKey("subscription_plans.id"), nullable=False)

    status = Column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False
    )

    current_period_start = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
    current_period_end = Column(DateTime, nullable=True)

    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan")
