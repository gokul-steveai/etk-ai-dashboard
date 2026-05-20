from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from auth import create_access_token
from models import SubscriptionPlan, User, UserSubscription
from schemas import (
    BaseResponse,
    PlanName,
    SubscriptionStatus,
    TokenResponse,
    UserPlanData,
)


async def ensure_user_has_free_plan(db: AsyncSession, user_id: str) -> None:
    """
    Defensively updates or assigns the default FREE plan mapping
    to any new account or unassigned legacy database user.
    """
    # 1. Look for an existing mapping record row
    sub_res = await db.execute(
        select(UserSubscription).filter(UserSubscription.user_id == user_id)
    )
    existing_subscription = sub_res.scalars().first()

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
            access_token=access_token,
            token_type="bearer",
            subscription=subscription_data,
        ),
    )


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
    )
