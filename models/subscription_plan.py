import uuid
from datetime import datetime, timezone

from sqlalchemy import CHAR, JSON, Boolean, Column, DateTime, Enum, Integer, String

from core.database import Base
from enums import PlanName


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    name = Column(Enum(PlanName), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # --- Client Quota Fields ---
    max_saved_queries = Column(Integer, default=0, nullable=False)  # Free=0, Basic=2
    max_compare_countries = Column(Integer, default=0, nullable=False)
    max_users = Column(Integer, default=1, nullable=False)  # Basic=1, Enterprise=5+

    # --- Client Features ---
    can_export = Column(
        Boolean, default=False, nullable=False
    )  # Blocks PDF/XLSX generation
    has_risk_intelligence = Column(Boolean, default=False, nullable=False)
    has_watchlist_access = Column(Boolean, default=False, nullable=False)
    has_partner_access = Column(Boolean, default=False, nullable=False)

    # Subscription plan features JSON
    features = Column(JSON, nullable=False, default=[])

    stripe_price_id = Column(String(255), unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
