from enum import Enum


class PlanName(str, Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELED = "canceled"
    EXPIRED = "expired"
