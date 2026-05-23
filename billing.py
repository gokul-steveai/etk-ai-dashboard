from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Customer, Invoice, SignatureVerificationError, Webhook
from stripe.checkout import Session

from config import settings
from database import get_db
from models import User
from schemas import (
    BaseResponse,
    DashboardInvoiceItem,
    PlanName,
    SubscriptionStatus,
    UnifiedBillingDashboardData,
)
from utils import (
    fetch_subscription_by_id,
    fetch_subscription_plan_by_name,
    fetch_user_subscription,
    fetch_user_subscription_by_sub_id,
    get_current_user,
    get_user_active_plan,
)

router = APIRouter(
    prefix="/billing",
    tags=["Subscription and Payment Management"],
)


@router.post("/create-checkout-session")
async def create_checkout_session(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a secure, hosted Stripe checkout window link mapping
    the active customer context dynamically via database Price IDs.
    """

    sub_plan = await fetch_subscription_by_id(db, subscription_id)
    if not sub_plan or not sub_plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested plan is either invalid or unavailable.",
        )

    # Check if the user is already subscribed to the plan
    user_sub = await fetch_user_subscription(db, str(current_user.id))
    if (
        user_sub
        and user_sub.stripe_subscription_id == subscription_id
        and user_sub.status == SubscriptionStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already subscribed to this plan.",
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

        frontend_base_url = settings.FRONTEND_URL.rstrip("/")
        dynamic_success_url = (
            f"{frontend_base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        )

        # Create the checkout session
        session = Session.create(
            api_key=settings.STRIPE_SECRET_KEY,
            mode="subscription",
            line_items=[
                {
                    "price": sub_plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            metadata={
                "user_id": str(current_user.id),
                "plan": sub_plan.name.upper(),
            },
            success_url=dynamic_success_url,
            customer=stripe_customer_id if stripe_customer_id else None,
            customer_email=current_user.email if not stripe_customer_id else None,
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
            invoices = Invoice.list(
                customer=user_sub.stripe_customer_id,
                limit=24,
                api_key=settings.STRIPE_SECRET_KEY,
            )

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
        max_users=plan_data.max_users,
        can_export=plan_data.can_export,
        has_risk_intelligence=plan_data.has_risk_intelligence,
        has_watchlist_access=plan_data.has_watchlist_access,
        has_partner_access=plan_data.has_partner_access,
        billing_history=invoice_history,
    )

    return BaseResponse(
        success=True,
        message="Unified billing metrics aggregated successfully.",
        data=dashboard_payload,
    )


@router.post(
    "/webhook", status_code=status.HTTP_200_OK, response_model=BaseResponse[str]
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> BaseResponse[str]:
    """
    Endpoint to receive and process Stripe webhook events. Handles subscription lifecycle events
    and updates the local database accordingly to maintain synchronization with Stripe's billing status.
    """
    payload = await request.body()

    try:
        event = Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
            api_key=settings.STRIPE_SECRET_KEY,
        )
    except (ValueError, SignatureVerificationError) as e:
        print(f"❌ Webhook signature verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature verification.",
        )

    event_type = event["type"]
    session_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = session_data["metadata"] if "metadata" in session_data else {}
        user_id = metadata["user_id"] if "user_id" in metadata else None
        plan_name = metadata["plan"] if "plan" in metadata else str(PlanName.BASIC)

        stripe_customer = (
            session_data["customer"] if "customer" in session_data else None
        )
        stripe_sub = (
            session_data["subscription"] if "subscription" in session_data else None
        )

        if user_id and stripe_sub:
            plan_obj = await fetch_subscription_plan_by_name(db, plan_name)
            subscription = await fetch_user_subscription(db, user_id)

            if subscription and plan_obj:
                subscription.plan_id = plan_obj.id
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.stripe_customer_id = stripe_customer
                subscription.stripe_subscription_id = stripe_sub
                subscription.updated_at = datetime.now(timezone.utc).replace(
                    tzinfo=None
                )

                await db.commit()
                print(
                    f"[INFO] Webhook [checkout.session.completed] - Provisioned User ID: {user_id} with Sub ID: {stripe_sub}"
                )

    elif event_type == "invoice.payment_succeeded":
        stripe_sub = (
            session_data["subscription"] if "subscription" in session_data else None
        )

        if stripe_sub:
            subscription = await fetch_user_subscription_by_sub_id(db, stripe_sub)

            if subscription:
                period_end = int(datetime.now(timezone.utc).timestamp()) + 2592000
                if "lines" in session_data and "data" in session_data["lines"]:
                    lines_data = session_data["lines"]["data"]
                    if len(lines_data) > 0 and "period" in lines_data[0]:
                        period_end = lines_data[0]["period"]["end"]

                subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_end = datetime.fromtimestamp(
                    period_end, timezone.utc
                ).replace(tzinfo=None)
                subscription.updated_at = datetime.now(timezone.utc).replace(
                    tzinfo=None
                )

                await db.commit()
                print(
                    f"[INFO] Webhook [invoice.payment_succeeded] - Subscription {stripe_sub} extended until {subscription.current_period_end}"
                )

    elif event_type == "customer.subscription.updated":
        stripe_sub = session_data["id"]
        subscription = await fetch_user_subscription_by_sub_id(db, stripe_sub)

        if subscription:
            new_status = session_data["status"]
            subscription.status = SubscriptionStatus(new_status.upper())
            subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

            await db.commit()
            print(
                f"[INFO] Webhook [customer.subscription.updated] - Subscription {stripe_sub} marked as {new_status}"
            )

    elif event_type == "customer.subscription.deleted":
        stripe_sub = session_data["id"]
        subscription = await fetch_user_subscription_by_sub_id(db, stripe_sub)

        if subscription:
            free_plan = await fetch_subscription_plan_by_name(db, PlanName.FREE)
            subscription.plan_id = free_plan.id
            subscription.status = SubscriptionStatus.CANCELED
            subscription.stripe_subscription_id = None
            subscription.current_period_end = None
            subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

            await db.commit()
            print(
                f"[WARN] Webhook [customer.subscription.deleted] - Subscription {stripe_sub} canceled. User dropped to FREE tier."
            )

    return BaseResponse(
        success=True, message="Webhook processed successfully.", data=None
    )
