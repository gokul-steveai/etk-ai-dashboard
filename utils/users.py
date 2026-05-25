from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from enums import PlanName, SubscriptionStatus
from models.subscription_plan import SubscriptionPlan
from models.user_subscription import UserSubscription
from models.users import User
from schemas.subscription import UserPlanData
from utils.subscription import fetch_user_subscription


async def find_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Fetches a user by string UUID asynchronously."""
    result = await db.execute(
        select(User).filter(User.id == user_id, User.deleted_at == None)
    )
    return result.scalars().first()


async def find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Fetches a user by email using Asynchronous SQLAlchemy 2.0 select execution."""
    result = await db.execute(
        select(User).filter(User.email == email, User.deleted_at == None)
    )
    return result.scalars().first()


async def ensure_user_has_free_plan(db: AsyncSession, user_id: str) -> None:
    """
    Defensively updates or assigns the default FREE plan mapping
    to any new account or unassigned legacy database user.
    """
    # Look for an existing mapping record row
    existing_subscription = await fetch_user_subscription(db, user_id)

    if existing_subscription:
        return

    plan_res = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.name == PlanName.FREE)
    )
    free_plan = plan_res.scalars().first()

    if not free_plan:
        raise RuntimeError(
            "CRITICAL: Master SubscriptionPlan tables must be seeded before user routing."
        )

    new_subscription = UserSubscription(
        user_id=user_id,
        plan_id=free_plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.now(timezone.utc).replace(tzinfo=None),
        current_period_end=None,  # Infinite lifetime boundary for free account tiers
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(new_subscription)
    await db.commit()


async def get_user_active_plan(db: AsyncSession, user_id: str) -> UserPlanData:
    """
    Asynchronously fetches a user's active subscription mapping row and
    associated configuration limits, returning a structured Pydantic object.
    """
    result = await db.execute(
        select(UserSubscription)
        .options(
            joinedload(UserSubscription.plan)
        )  # Eager load the Plan metadata template
        .filter(UserSubscription.user_id == user_id)
    )
    sub = result.scalars().first()

    # Fallback to prevent app crashes if a row is missing during runtime evaluation
    if not sub:
        return UserPlanData(
            plan_name=PlanName.FREE,
            status=SubscriptionStatus.ACTIVE,
            max_saved_queries=0,
            max_compare_countries=2,
            features={"time_limit_gate": True, "export_formats": False},
        )

    return UserPlanData(
        plan_name=sub.plan.name,
        status=sub.status,
        max_saved_queries=sub.plan.max_saved_queries,
        max_compare_countries=sub.plan.max_compare_countries,
        features=sub.plan.features,
        max_users=sub.plan.max_users or 1,
        can_export=sub.plan.can_export or False,
        has_risk_intelligence=sub.plan.has_risk_intelligence or False,
        has_watchlist_access=sub.plan.has_watchlist_access or False,
        has_partner_access=sub.plan.has_partner_access or False,
    )
