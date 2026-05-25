from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CHAR, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from core.database import Base
from enums import SubscriptionStatus


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()), index=True)
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
