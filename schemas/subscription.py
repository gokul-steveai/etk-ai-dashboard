from typing import List

from pydantic import Field

from enums import PlanName, SubscriptionStatus
from schemas.base import BaseSchema


class PlanLimitsMixin(BaseSchema):
    """Reusable subscription plan limits and feature access."""

    max_users: int = Field(
        default=1,
        ge=1,
        description="Maximum number of users allowed",
        examples=[5],
    )

    max_saved_queries: int = Field(
        default=0,
        ge=0,
        description="Maximum number of saved queries allowed",
        examples=[100],
    )

    max_compare_countries: int = Field(
        default=0,
        ge=0,
        description="Maximum number of countries that can be compared",
        examples=[10],
    )

    can_export: bool = Field(
        default=False,
        description="Indicates whether export functionality is enabled",
        examples=[True],
    )

    has_risk_intelligence: bool = Field(
        default=False,
        description="Indicates whether risk intelligence access is enabled",
        examples=[True],
    )

    has_watchlist_access: bool = Field(
        default=False,
        description="Indicates whether watchlist access is enabled",
        examples=[True],
    )

    has_partner_access: bool = Field(
        default=False,
        description="Indicates whether partner access is enabled",
        examples=[False],
    )


class BaseSubscriptionSchema(BaseSchema):
    """Reusable subscription metadata schema."""

    plan_name: PlanName = Field(
        ...,
        description="Current subscription plan name",
        examples=["pro"],
    )

    status: SubscriptionStatus = Field(
        ...,
        description="Current subscription status",
        examples=["active"],
    )

    features: List[str] = Field(
        default_factory=list,
        description="List of enabled subscription features",
        examples=[
            [
                "Unlimited saved searches",
                "Export reports",
                "Country comparison",
            ]
        ],
    )


class UserPlanData(BaseSubscriptionSchema, PlanLimitsMixin):
    """Authenticated user subscription details."""

    pass
