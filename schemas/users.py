from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from schemas.subscription import UserPlanData


class UserProfile(BaseModel):
    id: str
    email: str
    profile_image: str
    first_name: str
    last_name: str
    created_at: datetime


class UserData(UserProfile):
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
    user_id: str


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
