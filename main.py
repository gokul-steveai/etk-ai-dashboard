import base64
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import requests
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.auth.transport import requests as google_requests
from google.oauth2.id_token import verify_oauth2_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Subscription

from auth import generate_otp, hash_password, send_email, verify_password
from billing import router as billing_router
from config import settings
from database import engine, get_db
from models import Base, CompanyProfile, User
from schemas import (
    BaseResponse,
    CompanyProfileCreate,
    ForgotPassword,
    GoogleAuthRequest,
    LinkedInAuthRequest,
    ProfileData,
    ResetPassword,
    SubscriptionStatus,
    TokenResponse,
    UserCreate,
    UserData,
    UserLogin,
    UserProfilePatchRequest,
)
from utils import (
    fetch_user_subscription,
    find_user_by_email,
    find_user_by_id,
    generate_auth_response,
    get_current_user,
    get_user_active_plan,
)

UPLOAD_DIR = "static/profile_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(root_path="/api", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(billing_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = error["loc"][-1]
    msg = error["msg"]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "message": f"{field}: {msg}"},
    )


@app.post(
    "/signup",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user, ensuring email uniqueness, and returns an authentication token along with subscription details."""

    existing_user = await find_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    new_user = User(email=user.email, password=hash_password(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return await generate_auth_response(db, new_user, "Signup successful.")


@app.post(
    "/login",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates a user by email and password, enforcing plan checks, and returns an authentication token along with subscription details."""
    db_user = await find_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    return await generate_auth_response(db, db_user, "Login successful.")


@app.post(
    "/forgot-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
async def forgot_password(data: ForgotPassword, db: AsyncSession = Depends(get_db)):
    """Initiates the forgot password flow by generating a time-limited OTP and sending it to the user's email."""
    user = await find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=5
    )

    await db.commit()
    send_email(user.email, otp)

    return {"message": "OTP sent to your email"}


@app.post(
    "/reset-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    """Resets the user's password using the provided OTP."""
    user = await find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check OTP
    if user.otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP"
        )

    # Check expiry
    if not user.otp_expiry or datetime.now(timezone.utc) > user.otp_expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired"
        )

    # Update password
    user.password = hash_password(data.new_password)

    # Clear OTP
    user.otp = None
    user.otp_expiry = None

    await db.commit()

    return {"message": "Password reset successful"}


@app.post(
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


async def handle_oauth_user_provisioning(
    db: AsyncSession,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    social_avatar_url: Optional[str] = None,
) -> BaseResponse[TokenResponse]:
    """
    Resolves an OAuth user by email, handles fallback delta properties,
    and provisions profiles with unified social media image URLs.
    """
    user = await find_user_by_email(db, email)

    if not user:
        user = User(
            id=str(uuid4()),
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_image=social_avatar_url,
            password=None,
            otp=None,
            otp_expiry=None,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.profile_image and social_avatar_url:
            user.profile_image = social_avatar_url
            user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

    return await generate_auth_response(db, user, "Login successful.")


@app.post(
    "/auth/google",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def google_authentication(
    payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    """Receives the Google ID token from the frontend, validates it against Google's token verification API, and delegates user provisioning to the shared authentication layer."""
    if not payload.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google ID token in request payload.",
        )
    try:
        id_info = verify_oauth2_token(
            payload.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = id_info.get("email")
        f_name = id_info.get("given_name")
        l_name = id_info.get("family_name")
        avatar = id_info.get("picture")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token payload invalid.",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credentials: {str(e)}",
        )

    return await handle_oauth_user_provisioning(
        db, email, first_name=f_name, last_name=l_name, social_avatar_url=avatar
    )


@app.post(
    "/auth/linkedin",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def linkedin_authentication(
    payload: LinkedInAuthRequest, db: AsyncSession = Depends(get_db)
):
    """
    Receives the LinkedIn access_token from the frontend, validates it against
    LinkedIn's UserInfo API, and delegates user provisioning to the shared authentication layer.
    """
    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing LinkedIn access token.",
        )
    try:
        headers = {"Authorization": f"Bearer {payload.access_token}"}
        response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)

        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify token with LinkedIn or token has expired.",
            )

        user_info = response.json()
        email = user_info.get("email")
        f_name = user_info.get("given_name")
        l_name = user_info.get("family_name")
        avatar = user_info.get("picture")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn profile missing verified email address.",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"LinkedIn authentication failed: {str(e)}",
        )

    return await handle_oauth_user_provisioning(
        db, email, first_name=f_name, last_name=l_name, social_avatar_url=avatar
    )


@app.get(
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


@app.get(
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
        ),
    )


@app.delete(
    "/user/account", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
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


@app.patch(
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
