from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    message: str


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class GoogleAuthRequest(BaseModel):
    """Request payload for Google login."""

    id_token: str = Field(
        ..., description="The cryptographically signed ID token from NextAuth/Auth.js"
    )

    class Config:
        json_schema_extra = {
            "example": {"id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImU0N..."}
        }


class LinkedInAuthRequest(BaseModel):
    """Request payload for LinkedIn login."""

    access_token: str = Field(
        ...,
        description="The access token returned by NextAuth/Auth.js from the LinkedIn provider",
    )

    class Config:
        json_schema_extra = {"example": {"access_token": "AQX4_abc123XYZ..."}}


class BaseResponse(BaseModel, Generic[T]):
    """Standardized top-level API envelope structure for all responses."""

    success: bool = True
    message: str
    data: Optional[T] = None


class BillingPlan(StrEnum):
    BASIC = "BASIC"


class PlanName(StrEnum):
    FREE = "FREE"
    BASIC = "BASIC"
    INDIVIDUAL = "INDIVIDUAL"
    RESEARCHER = "RESEARCHER"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELED = "canceled"
    EXPIRED = "expired"


class UserPlanData(BaseModel):
    plan_name: PlanName
    status: SubscriptionStatus
    max_saved_queries: int
    max_compare_countries: int
    features: Dict[str, Any]


class UserProfile(BaseModel):
    id: str
    email: str
    profile_image: str
    first_name: str
    last_name: str
    created_at: datetime


class UserData(UserProfile):
    subscription: UserPlanData


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
    subscription: UserPlanData


class ProfileData(BaseModel):
    id: str
    user_id: str
    data: dict


class UserInfoData(BaseModel):
    user_id: str
    email: Optional[str] = None
    profile: dict


class CompanyProfileCreate(BaseModel):
    user_id: str
    company_profile: str

    countries: list
    company_intentions: list
    industries: list

    business_type: list
    business_stage: list
    business_turnover: list
    business_timeline: list
    business_clients: list
    business_deal_size: list
    business_intentions: list
    business_product_adaptation: list
    business_international_experience: list
    business_international_enquiries: list
    business_budget: list
    business_growth_export_team: list
    business_preferences: list
    business_risk_appetite: list
    business_local_partners: list
    business_type_of_support: list


class UserIdRequest(BaseModel):
    user_id: UUID


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
    max_saved_queries: int
    max_compare_countries: int
    features: dict

    # History
    billing_history: List[DashboardInvoiceItem]


class UserProfilePatchRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image: Optional[str] = None  # Base64

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "profile_image": "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==",
            }
        }
