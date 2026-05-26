from datetime import datetime
from typing import List, Optional

from pydantic import Field

from enums import PlanName
from schemas.base import BaseSchema
from schemas.subscription import PlanLimitsMixin, UserPlanData


class DashboardInvoiceItem(BaseSchema):
    """Billing invoice item schema."""

    id: str = Field(
        ...,
        description="Unique invoice identifier",
        examples=["inv_1QxYZaBc123"],
    )

    number: str = Field(
        ...,
        description="Invoice number",
        examples=["INV-2026-001"],
    )

    amount_paid: float = Field(
        ...,
        ge=0,
        description="Amount paid for the invoice",
        examples=[49.99],
    )

    currency: str = Field(
        ...,
        description="Invoice currency",
        examples=["USD"],
    )

    status: str = Field(
        ...,
        description="Current invoice payment status",
        examples=["paid"],
    )

    created_at: datetime = Field(
        ...,
        description="Invoice creation timestamp",
        examples=["2026-05-24T10:30:00Z"],
    )

    invoice_pdf: Optional[str] = Field(
        default=None,
        description="URL to download invoice PDF",
        examples=["https://billing.example.com/invoice.pdf"],
    )

    hosted_invoice_url: Optional[str] = Field(
        default=None,
        description="Hosted invoice URL",
        examples=["https://billing.example.com/invoices/inv_123"],
    )


class SubscriptionOverviewSchema(UserPlanData):
    """Shared subscription overview fields."""

    current_period_start: datetime = Field(
        ...,
        description="Subscription billing period start date",
        examples=["2026-05-01T00:00:00Z"],
    )

    current_period_end: Optional[datetime] = Field(
        default=None,
        description="Subscription billing period end date",
        examples=["2026-06-01T00:00:00Z"],
    )

    is_active: bool = Field(
        default=True,
        description="Indicates whether the subscription is active",
        examples=[True],
    )


class UnifiedBillingDashboardData(SubscriptionOverviewSchema):
    """Unified billing dashboard response."""

    billing_history: List[DashboardInvoiceItem] = Field(
        default_factory=list,
        description="User billing and invoice history",
    )


class BaseSubscriptionPlanSchema(PlanLimitsMixin):
    """Reusable subscription plan fields."""

    id: str = Field(
        ...,
        description="Unique subscription plan identifier",
        examples=["plan_pro_monthly"],
    )

    plan_name: PlanName = Field(
        ...,
        description="Subscription plan name",
        examples=["pro"],
    )

    description: str = Field(
        ...,
        description="Detailed subscription plan description",
        examples=["Professional plan with advanced analytics and export features"],
    )

    features: List[str] = Field(
        ...,
        description="List of plan features",
        examples=[
            [
                "Unlimited saved queries",
                "Advanced analytics",
                "Export access",
            ]
        ],
    )

    amount: float = Field(
        ...,
        ge=0,
        description="Subscription plan price",
        examples=[49.99],
    )

    currency: str = Field(
        ...,
        description="Billing currency",
        examples=["USD"],
    )

    interval: str = Field(
        ...,
        description="Billing interval",
        examples=["monthly"],
    )

    is_custom_pricing: bool = Field(
        default=False,
        description="Indicates whether the plan uses custom pricing",
        examples=[False],
    )

    is_active: bool = Field(
        default=True,
        description="Indicates whether the plan is currently active",
        examples=[True],
    )

    created_at: datetime = Field(
        ...,
        description="Plan creation timestamp",
        examples=["2026-01-15T09:00:00Z"],
    )


class SubscriptionPlanResponse(BaseSubscriptionPlanSchema):
    """Subscription plan response schema."""

    pass


class CreateCheckoutSessionResponse(BaseSchema):
    """Response schema for creating a checkout session."""

    checkout_url: str = Field(
        ...,
        description="URL to redirect the user for payment",
        examples=["https://checkout.example.com/session/abc123"],
    )
