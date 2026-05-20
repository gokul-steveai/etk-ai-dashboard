from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Any, Dict, Generic, Optional, TypeVar

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


class UserData(BaseModel):
    id: str
    email: str
    subscription: UserPlanData


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
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
