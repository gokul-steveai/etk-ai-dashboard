from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Customer, Invoice
from stripe.checkout import Session

from config import settings
from database import get_db
from models import User
from schemas import (
    BaseResponse,
    BillingPlan,
    DashboardInvoiceItem,
    UnifiedBillingDashboardData,
)
from utils import (
    fetch_subscription_plan_by_name,
    fetch_user_subscription,
    get_current_user,
    get_user_active_plan,
)

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
)


STRIPE_PRICES: dict[BillingPlan, str] = {"BASIC": "price_1TZQKXCT0zz3DDk5VsjtZB3A"}


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan: BillingPlan,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a secure, hosted Stripe checkout window link mapping
    the active customer context dynamically via database Price IDs.
    """
    if plan not in STRIPE_PRICES or STRIPE_PRICES[plan] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan name"
        )

    sub_plan = await fetch_subscription_plan_by_name(db, plan)

    if not plan or not sub_plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested plan is either invalid or does not require a billing session.",
        )

    # Check if the user already possesses a Stripe Customer ID token
    user_sub = await fetch_user_subscription(db, str(current_user.id))

    stripe_customer_id = user_sub.stripe_customer_id if user_sub else None

    try:
        # If the user doesn't have a Customer ID yet, create one in Stripe
        if not stripe_customer_id:
            customer = Customer.create(
                api_key=settings.STRIPE_SECRET_KEY,
                email=current_user.email,
                metadata={"user_id": str(current_user.id)},
            )
            stripe_customer_id = customer.id

            # Save it locally right away so we don't duplicate customer profiles later
            if user_sub:
                user_sub.stripe_customer_id = stripe_customer_id
                await db.commit()

        # Create the checkout session
        session = Session.create(
            api_key=settings.STRIPE_SECRET_KEY,
            mode="subscription",
            line_items=[
                {
                    "price": STRIPE_PRICES[plan],
                    "quantity": 1,
                }
            ],
            metadata={
                "user_id": str(current_user.id),
                "plan": plan.upper(),
            },
            success_url="https://oauth.pstmn.io/v1/browser-callback?session_id={CHECKOUT_SESSION_ID}",
            # cancel_url=settings.STRIPE_CANCEL_URL,
        )

        return BaseResponse(
            success=True,
            message="Checkout session link built successfully.",
            data={"checkout_url": session.url},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe interaction failure: {str(e)}",
        )


@router.get(
    "/dashboard",
    response_model=BaseResponse[UnifiedBillingDashboardData],
    status_code=status.HTTP_200_OK,
)
async def get_unified_billing_dashboard(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Unified Production Dashboard API. Compiles local account quotas, active
    payment options, and invoice history records in a single execution block.
    """
    plan_data = await get_user_active_plan(db, str(current_user.id))

    user_sub = await fetch_user_subscription(db, str(current_user.id))

    invoice_history: List[DashboardInvoiceItem] = []

    # If a stripe customer connection token exists, fetch active payment metrics
    if user_sub and user_sub.stripe_customer_id:
        try:
            # Fetch the recent history transactions log (up to last 24 iterations)
            invoices = Invoice.list(customer=user_sub.stripe_customer_id, limit=24)
            for inv in invoices.data:
                invoice_history.append(
                    DashboardInvoiceItem(
                        id=inv.id,
                        number=inv.number or "N/A",
                        amount_paid=float(
                            inv.amount_paid / 100
                        ),  # Convert standard cents cleanly
                        currency=inv.currency.upper(),
                        status=inv.status,
                        created_at=datetime.fromtimestamp(
                            inv.created, timezone.utc
                        ).replace(tzinfo=None),
                        invoice_pdf=inv.invoice_pdf,
                        hosted_invoice_url=inv.hosted_invoice_url,
                    )
                )

        except Exception as stripe_err:
            # Prevent minor network connection anomalies from locking users out of the whole system dashboard
            print(
                f"⚠️ Non-breaking log: Stripe dashboard sync variance encountered: {str(stripe_err)}"
            )

    # 5. Pack the combined components package together cleanly
    dashboard_payload = UnifiedBillingDashboardData(
        plan_name=plan_data.plan_name,
        status=plan_data.status,
        current_period_start=(
            user_sub.current_period_start if user_sub else datetime.now()
        ),
        current_period_end=user_sub.current_period_end if user_sub else None,
        max_saved_queries=plan_data.max_saved_queries,
        max_compare_countries=plan_data.max_compare_countries,
        features=plan_data.features,
        billing_history=invoice_history,
    )

    return BaseResponse(
        success=True,
        message="Unified billing metrics aggregated successfully.",
        data=dashboard_payload,
    )
