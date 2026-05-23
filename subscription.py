from datetime import datetime, timezone
from typing import List

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import SubscriptionPlan, User
from schemas import BaseResponse, PlanName, SubscriptionPlanResponse
from utils import get_current_user

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)


@router.get(
    "/",
    response_model=BaseResponse[List[SubscriptionPlanResponse]],
    status_code=status.HTTP_200_OK,
)
async def get_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to retrieve all subscriptions. Combines local database metadata
    with dynamic, real-time pricing configurations pulled from Stripe.
    """
    try:
        result = await db.execute(
            select(SubscriptionPlan).order_by(SubscriptionPlan.id.asc())
        )
        subscription_list = result.scalars().all()

        if not subscription_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscriptions found",
            )

        subscription_responses: List[SubscriptionPlanResponse] = []

        for sub in subscription_list:
            if sub.stripe_price_id:
                try:
                    stripe_price = stripe.Price.retrieve(
                        sub.stripe_price_id, api_key=settings.STRIPE_SECRET_KEY
                    )

                    unit_amount = (
                        stripe_price["unit_amount"]
                        if "unit_amount" in stripe_price
                        else None
                    )
                    amount = (
                        float(unit_amount / 100) if unit_amount is not None else 0.0
                    )
                    is_custom_pricing = unit_amount is None

                    interval = "one_time"
                    if (
                        "recurring" in stripe_price
                        and stripe_price["recurring"] is not None
                    ):
                        interval = (
                            stripe_price["recurring"]["interval"]
                            if "interval" in stripe_price["recurring"]
                            else "month"
                        )

                    currency = (
                        stripe_price["currency"].upper()
                        if "currency" in stripe_price
                        else "USD"
                    )

                except Exception as stripe_err:
                    print(
                        f"❌ Stripe fetch error for Price ID {sub.stripe_price_id}: {str(stripe_err)}"
                    )
                    amount = 0.0
                    is_custom_pricing = True
                    interval = "one_time"
                    currency = "USD"

            else:
                amount = 0.0
                is_custom_pricing = (
                    sub.name.upper() != PlanName.FREE
                )  # FREE isn't custom pricing, Enterprise is
                interval = "one_time"
                currency = "USD"

            subscription_responses.append(
                SubscriptionPlanResponse(
                    id=sub.id,
                    plan_name=sub.name,
                    description=sub.description or "",
                    features=sub.features or [""],
                    max_saved_queries=sub.max_saved_queries or 0,
                    max_compare_countries=sub.max_compare_countries or 0,
                    created_at=sub.created_at
                    or datetime.now(timezone.utc).replace(tzinfo=None),
                    amount=amount,
                    currency=currency,
                    interval=interval,
                    is_custom_pricing=is_custom_pricing,
                    is_active=sub.is_active if sub.is_active is not None else True,
                )
            )

        return BaseResponse(
            data=subscription_responses,
            message="Subscriptions retrieved successfully",
            success=True,
        )

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"❌ Core runtime failure in subscription mapping block: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compile and verify system subscription profiles.",
        )
