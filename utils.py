from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from fastapi.params import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from auth import create_access_token, verify_token
from database import get_db
from models import SubscriptionPlan, User, UserSubscription
from schemas import (
    BaseResponse,
    PlanName,
    SubscriptionStatus,
    TokenResponse,
    UserPlanData,
    UserProfile,
)

security_scheme = HTTPBearer()


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


async def fetch_user_subscription(
    db: AsyncSession, user_id: str
) -> UserSubscription | None:
    sub_res = await db.execute(
        select(UserSubscription).filter(UserSubscription.user_id == user_id)
    )
    return sub_res.scalars().first()


async def fetch_subscription_plan_by_name(
    db: AsyncSession, plan_name: PlanName
) -> SubscriptionPlan | None:
    plan_res = await db.execute(
        select(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name)
    )
    return plan_res.scalars().first()


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
            email=user.email,
            access_token=access_token,
            token_type="bearer",
            subscription=subscription_data,
            user=UserProfile(
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                profile_image=user.profile_image or "",
                created_at=user.created_at,
                id=str(user.id),
                email=user.email,
            ),
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current authenticated user."""
    token = credentials.credentials

    try:
        payload = verify_token(token)

        if payload is None or payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token.",
            )

        email: str = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token.",
        )

    user = await find_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found."
        )

    return user
