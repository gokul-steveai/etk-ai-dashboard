from typing import List

from pydantic import BaseModel

from enums import PlanName, SubscriptionStatus


class UserPlanData(BaseModel):
    plan_name: PlanName
    status: SubscriptionStatus
    max_saved_queries: int
    max_compare_countries: int
    features: List[str]

    max_users: int = 1
    can_export: bool = False
    has_risk_intelligence: bool = False
    has_watchlist_access: bool = False
    has_partner_access: bool = False
