from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enums import PlanName
from models.subscription_plan import SubscriptionPlan
from models.user_subscription import UserSubscription


async def fetch_user_subscription(
    db: AsyncSession, user_id: str
) -> UserSubscription | None:
    """Fetches the UserSubscription mapping for a given user ID, returning the full SQLAlchemy model instance."""
    sub_res = await db.execute(
        select(UserSubscription).filter(UserSubscription.user_id == user_id)
    )
    return sub_res.scalars().first()


async def fetch_subscription_plan_by_name(
    db: AsyncSession, plan_name: PlanName
) -> SubscriptionPlan | None:
    """Fetches a subscription plan by its enumerated name, returning the full SQLAlchemy model instance."""
    plan_res = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name)
    )
    return plan_res.scalars().first()


async def fetch_user_subscription_by_sub_id(
    db: AsyncSession, stripe_subscription_id: str
) -> UserSubscription | None:
    """Fetches a user subscription by Stripe subscription ID."""
    sub_res = await db.execute(
        select(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    return sub_res.scalars().first()


async def fetch_subscription_by_id(
    db: AsyncSession, sub_id: str
) -> SubscriptionPlan | None:
    """Fetches a subscription plan by its ID."""
    plan_res = await db.execute(
        select(SubscriptionPlan).filter(
            SubscriptionPlan.id == sub_id, SubscriptionPlan.is_active == True
        )
    )
    return plan_res.scalars().first()
