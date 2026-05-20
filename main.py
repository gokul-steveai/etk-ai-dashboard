from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from auth import (
    generate_otp,
    hash_password,
    send_email,
    verify_password,
    verify_token,
)
from auth_utils import generate_auth_response, get_user_active_plan
from database import engine, get_db
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from uuid import UUID, uuid4
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from config import settings
from schemas import (
    BaseResponse,
    ForgotPassword,
    GoogleAuthRequest,
    LinkedInAuthRequest,
    ResetPassword,
    UserCreate,
    UserLogin,
    TokenResponse,
    ProfileData,
    CompanyProfileCreate,
    UserData,
)
from models import User, CompanyProfile, Base
from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport import requests as google_requests
import requests


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(root_path="/api", lifespan=lifespan)

security_scheme = HTTPBearer()


async def find_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Fetches a user by email using Asynchronous SQLAlchemy 2.0 select execution."""
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def find_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Fetches a user by string UUID asynchronously."""
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = verify_token(token)

        if payload is None or payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token.",
            )

        email: str = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token.",
        )

    user = await find_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found."
        )

    return user


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
    db: AsyncSession, email: str
) -> BaseResponse[TokenResponse]:
    """
    Resolves an OAuth user by email, registers them if missing,
    generates a system JWT access token.
    """
    user = await find_user_by_email(db, email)

    if not user:
        user = User(
            id=str(uuid4()), email=email, password=None, otp=None, otp_expiry=None
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

    return await generate_auth_response(db, user, "Login successful.")


@app.post(
    "/auth/google",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def google_authentication(
    payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
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

    return await handle_oauth_user_provisioning(db, email)


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
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify token with LinkedIn or token has expired.",
            )
        user_info = response.json()
        email = user_info.get("email")
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

    return await handle_oauth_user_provisioning(db, email)


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
            id=str(current_user.id), email=current_user.email, subscription=plan
        ),
    )
