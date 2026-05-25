from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from enums import PlanName, SubscriptionStatus


class DashboardInvoiceItem(BaseModel):
    id: str
    number: str
    amount_paid: float
    currency: str
    status: str
    created_at: datetime
    invoice_pdf: Optional[str] = None
    hosted_invoice_url: Optional[str] = None


class UnifiedBillingDashboardData(BaseModel):
    # Plan
    plan_name: PlanName
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: Optional[datetime] = None
    features: List[str]
    is_active: bool = True

    max_users: int = 1
    max_saved_queries: int = 0
    max_compare_countries: int = 0
    can_export: bool = False
    has_risk_intelligence: bool = False
    has_watchlist_access: bool = False
    has_partner_access: bool = False

    # History
    billing_history: List[DashboardInvoiceItem]


class SubscriptionPlanResponse(BaseModel):
    id: str
    plan_name: str
    description: str
    features: List[str]
    amount: float
    currency: str
    interval: str
    is_custom_pricing: bool = False
    created_at: datetime
    is_active: bool = True

    max_users: int = 1
    max_saved_queries: int = 0
    max_compare_countries: int = 0
    can_export: bool = False
    has_risk_intelligence: bool = False
    has_watchlist_access: bool = False
    has_partner_access: bool = False
