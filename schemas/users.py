from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from schemas.base import BaseSchema
from schemas.subscription import UserPlanData


class UserIdMixin(BaseSchema):
    """Reusable user identifier schema."""

    user_id: str = Field(
        ...,
        description="Unique user identifier",
        examples=["abcd1234-5678-90ab-cdef-1234567890ab"],
    )


class UserNameMixin(BaseSchema):
    """Reusable user name schema."""

    first_name: str = Field(
        ...,
        description="User first name",
        examples=["John"],
    )

    last_name: str = Field(
        ...,
        description="User last name",
        examples=["Doe"],
    )


class UserProfileBase(UserNameMixin):
    """Reusable user profile fields."""

    id: str = Field(
        ...,
        description="Unique UUID user identifier",
        examples=["abcd1234-5678-90ab-cdef-1234567890ab"],
    )

    email: EmailStr = Field(
        ...,
        description="Registered user email address",
        examples=["john.doe@example.com"],
    )

    profile_image: Optional[str] = Field(
        default=None,
        description="User profile image URL or base64 encoded image",
        examples=[
            "https://cdn.example.com/profile/john-doe.png",
        ],
    )

    created_at: datetime = Field(
        ...,
        description="User account creation timestamp",
        examples=["2026-05-24T10:30:00Z"],
    )


class UserProfile(UserProfileBase):
    """Public user profile response schema."""

    pass


class UserData(UserProfileBase):
    """Authenticated user response schema."""

    subscription: UserPlanData = Field(
        ...,
        description="Active subscription details",
    )


class CompanyProfile(BaseSchema):
    """Reusable company profile fields."""

    company_profile: str = Field(
        ...,
        description="Detailed company profile summary",
        examples=["UK-based SaaS company focused on international trade analytics."],
    )

    countries: List[str] = Field(
        default_factory=list,
        description="Target countries for expansion",
        examples=[["United Kingdom", "Germany", "UAE"]],
    )

    company_intentions: List[str] = Field(
        default_factory=list,
        description="Business expansion intentions",
        examples=[["Export growth", "Market expansion"]],
    )

    industries: List[str] = Field(
        default_factory=list,
        description="Associated business industries",
        examples=[["Technology", "FinTech"]],
    )

    business_type: List[str] = Field(default_factory=list)
    business_stage: List[str] = Field(default_factory=list)
    business_turnover: List[str] = Field(default_factory=list)
    business_timeline: List[str] = Field(default_factory=list)
    business_clients: List[str] = Field(default_factory=list)
    business_deal_size: List[str] = Field(default_factory=list)
    business_intentions: List[str] = Field(default_factory=list)
    business_product_adaptation: List[str] = Field(default_factory=list)
    business_international_experience: List[str] = Field(default_factory=list)
    business_international_enquiries: List[str] = Field(default_factory=list)
    business_budget: List[str] = Field(default_factory=list)
    business_growth_export_team: List[str] = Field(default_factory=list)
    business_preferences: List[str] = Field(default_factory=list)
    business_risk_appetite: List[str] = Field(default_factory=list)
    business_local_partners: List[str] = Field(default_factory=list)
    business_type_of_support: List[str] = Field(default_factory=list)


class CompanyProfileCreate(UserIdMixin, CompanyProfile):
    """Company profile creation request schema."""

    pass


class ProfileData(BaseSchema):
    """User profile metadata schema."""

    id: str = Field(
        ...,
        description="Unique profile identifier",
        examples=["abcd1234-5678-90ab-cdef-1234567890ab"],
    )

    user_id: str = Field(
        ...,
        description="Associated user identifier",
        examples=["abcd1234-5678-90ab-cdef-1234567890ab"],
    )

    data: CompanyProfile = Field(
        ...,
        default_factory=CompanyProfile,
        description="Dynamic company profile data",
    )


class UserIdRequest(UserIdMixin):
    """User identifier request schema."""

    pass


class UserProfilePatchRequest(BaseSchema):
    """Partial user profile update schema."""

    first_name: Optional[str] = Field(
        default=None,
        description="Updated user first name",
        examples=["John"],
    )

    last_name: Optional[str] = Field(
        default=None,
        description="Updated user last name",
        examples=["Doe"],
    )

    profile_image: Optional[str] = Field(
        default=None,
        description="Base64 encoded profile image or image URL",
        examples=[
            "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        ],
    )
