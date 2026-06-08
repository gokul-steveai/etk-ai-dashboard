import base64
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Subscription

from core.config import settings
from core.database import get_db
from enums import SubscriptionStatus
from models.company_profile import CompanyProfile
from models.users import User
from schemas.base import BaseResponse
from schemas.users import (
    CompanyProfileCreate,
    ProfileData,
    UserData,
    UserProfilePatchRequest,
)
from utils.auth import get_current_user
from utils.subscription import fetch_user_subscription
from utils.users import find_user_by_id, get_user_active_plan

UPLOAD_DIR = "static/profile_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(tags=["User"])


@router.patch(
    "/user/account", response_model=BaseResponse[dict], status_code=status.HTTP_200_OK
)
async def update_user_account(
    payload: UserProfilePatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates the authenticated user profile. Handles Base64 image uploads and updates profile fields accordingly."""
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    # Process the Base64 Image string if present
    if "profile_image" in update_data and update_data["profile_image"]:
        base64_str = update_data["profile_image"]

        try:
            # Split the header (e.g., "data:image/png;base64,") from the actual data
            if "," in base64_str:
                header, base64_str = base64_str.split(",", 1)
            else:
                header = "data:image/png;base64"

            # Determine the file extension dynamically (png, jpeg, webp)
            ext = ".png"  # default fallback
            if "image/jpeg" in header or "image/jpg" in header:
                ext = ".jpg"
            elif "image/webp" in header:
                ext = ".webp"

            # Decode the text back into binary file data
            image_data = base64.b64decode(base64_str)

            # Enforce a max file size limit defensively (e.g., 5MB max)
            if len(image_data) > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size exceeds the 5MB limit.",
                )

            # Create a unique filename and file path for Plesk storage
            unique_filename = f"{current_user.id}{ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            # Write the binary data to your Plesk server directory disk
            with open(file_path, "wb") as f:
                f.write(image_data)

            # Update the database field to point to the local static URL path string
            current_user.profile_image = f"/static/profile_images/{unique_filename}"

        except Exception as err:
            if isinstance(err, HTTPException):
                raise err
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Base64 image data payload.",
            )

    if "first_name" in update_data:
        current_user.first_name = update_data["first_name"]
    if "last_name" in update_data:
        current_user.last_name = update_data["last_name"]

    current_user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(current_user)

    return BaseResponse(
        success=True,
        message="Profile updated successfully.",
        data={
            "id": str(current_user.id),
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "profile_image": current_user.profile_image,
        },
    )


@router.post(
    "/user-interests",
    response_model=BaseResponse[ProfileData],
    status_code=status.HTTP_201_CREATED,
)
async def create_company_profile(
    data: CompanyProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates or updates the company profile and user interests for the authenticated user."""
    try:
        if not current_user or current_user.id != data.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated.",
            )
        profile_data = {
            "company_profile": data.company_profile,
            "countries": data.countries,
            "company_intentions": data.company_intentions,
            "industries": data.industries,
            "business_type": data.business_type,
            "business_stage": data.business_stage,
            "business_turnover": data.business_turnover,
            "business_timeline": data.business_timeline,
            "business_clients": data.business_clients,
            "business_deal_size": data.business_deal_size,
            "business_intentions": data.business_intentions,
            "business_product_adaptation": data.business_product_adaptation,
            "business_international_experience": data.business_international_experience,
            "business_international_enquiries": data.business_international_enquiries,
            "business_budget": data.business_budget,
            "business_growth_export_team": data.business_growth_export_team,
            "business_preferences": data.business_preferences,
            "business_risk_appetite": data.business_risk_appetite,
            "business_local_partners": data.business_local_partners,
            "business_type_of_support": data.business_type_of_support,
        }

        result = await db.execute(
            select(CompanyProfile).filter(CompanyProfile.user_id == str(data.user_id))
        )
        existing_entry = result.scalars().first()

        if existing_entry:
            existing_entry.data = profile_data
            await db.commit()
            await db.refresh(existing_entry)
            return BaseResponse(
                success=True,
                message="Data updated successfully",
                data=ProfileData(
                    id=str(existing_entry.id),
                    user_id=str(existing_entry.user_id),
                    data=existing_entry.data,
                ),
            )
        else:
            new_entry = CompanyProfile(
                id=str(uuid4()), user_id=str(data.user_id), data=profile_data
            )
            db.add(new_entry)
            await db.commit()
            await db.refresh(new_entry)
            return BaseResponse(
                success=True,
                message="Data saved successfully",
                data=ProfileData(
                    id=str(new_entry.id),
                    user_id=str(new_entry.user_id),
                    data=new_entry.data,
                ),
            )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/get-user-interests/{user_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
)
async def get_user_interests(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches the user's profile data from the database and returns it as a dictionary.
    If the user has no profile, returns a default empty profile structure.
    """
    try:
        try:
            if not user_id or current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing or invalid user_id parameter.",
                )

            user_uuid = str(UUID(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format.",
            )

        default_profile = {
            "company_profile": "",
            "countries": [],
            "company_intentions": [],
            "industries": [],
            "business_type": [],
            "business_stage": [],
            "business_turnover": [],
            "business_timeline": [],
            "business_clients": [],
            "business_deal_size": [],
            "business_intentions": [],
            "business_product_adaptation": [],
            "business_international_experience": [],
            "business_international_enquiries": [],
            "business_budget": [],
            "business_growth_export_team": [],
            "business_preferences": [],
            "business_risk_appetite": [],
            "business_local_partners": [],
            "business_type_of_support": [],
        }

        user = await find_user_by_id(db, user_uuid)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        prof_res = await db.execute(
            select(CompanyProfile).filter(CompanyProfile.user_id == user_uuid)
        )
        profile = prof_res.scalars().first()

        return BaseResponse(
            success=True,
            message="Data fetched successfully",
            data={
                "user_id": str(user.id),
                "email": user.email,
                "profile": profile.data if profile else default_profile,
            },
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/get-user-id",
    response_model=BaseResponse[UserData],
    status_code=status.HTTP_200_OK,
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Returns the user's details for the authenticated user."""
    plan = await get_user_active_plan(db, str(current_user.id))
    return BaseResponse(
        success=True,
        message="User information retrieved successfully",
        data=UserData(
            id=str(current_user.id),
            email=current_user.email,
            subscription=plan,
            created_at=current_user.created_at,
            first_name=current_user.first_name or "",
            last_name=current_user.last_name or "",
            profile_image=current_user.profile_image or "",
            heatmap_fetch_count=current_user.heatmap_fetch_count,
        ),
    )


@router.get(
    "/heatmap/count", response_model=BaseResponse[dict], status_code=status.HTTP_200_OK
)
async def update_heatmap_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Updates the heatmap fetch count for the authenticated user."""
    await session.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(heatmap_fetch_count=User.heatmap_fetch_count + 1)
    )
    await session.commit()

    await session.refresh(current_user)

    return BaseResponse(
        data={
            "heatmap_fetch_count": current_user.heatmap_fetch_count,
            "user_id": str(current_user.id),
        },
        success=True,
        message="Heatmap fetch count updated successfully",
    )


# @router.delete(
#     "/user/account", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
# )
async def soft_delete_user_account(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Soft deletes the authenticated user profile and requests immediate
    subscription cancellation from Stripe if an active contract token exists.
    """
    # Look up their active subscription record context
    user_sub = await fetch_user_subscription(db, str(current_user.id))

    if user_sub and user_sub.stripe_subscription_id:
        try:
            # Cancel the subscription immediately at the end of the current billing period
            Subscription.modify(
                id=user_sub.stripe_subscription_id,
                api_key=settings.STRIPE_SECRET_KEY,
                cancel_at_period_end=True,
            )

            # Update local subscription status visibility state
            user_sub.status = SubscriptionStatus.CANCELED
            user_sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        except Exception as stripe_err:
            print(f"⚠️ Non-blocking Stripe cancel log exception: {str(stripe_err)}")

    # Apply the Soft Delete timestamp mark to the User model record
    current_user.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()

    return BaseResponse(
        success=True,
        message="Your profile has been successfully deactivated, and your subscription cancellation is pending.",
        data="Deactivation complete.",
    )
