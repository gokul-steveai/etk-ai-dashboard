from enum import Enum


class BillingPlan(str, Enum):
    BASIC = "BASIC"


class PlanName(str, Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    INDIVIDUAL = "INDIVIDUAL"
    RESEARCHER = "RESEARCHER"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELED = "canceled"
    EXPIRED = "expired"
