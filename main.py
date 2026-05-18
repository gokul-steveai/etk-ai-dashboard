from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from auth import generate_otp, send_email
from database import engine, SessionLocal
from auth import hash_password, verify_password, create_access_token
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from uuid import UUID, uuid4
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from auth import SECRET_KEY, ALGORITHM, GOOGLE_CLIENT_ID
from fastapi.exceptions import RequestValidationError
from schemas import (
    AuthTokenData,
    LinkedInAuthRequest,
    ProfileData,
    UserLogin,
    BaseResponse,
    TokenData,
    UserCreate,
    CompanyProfileCreate,
    GoogleAuthRequest,
    ResetPassword,
    ForgotPassword,
    UserData,
)
from models import User, Base, CompanyProfile
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests

Base.metadata.create_all(bind=engine)

app = FastAPI(root_path="/api")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def find_user_by_email(db: Session, email: str) -> Optional[User]:
    """fetches a user by email using SQLAlchemy 2.0 select statements."""
    result = db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


def find_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """fetches a user by string UUID."""
    result = db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = error["loc"][-1]
    msg = error["msg"]

    return JSONResponse(
        status_code=422,
        content={"success": False, "message": f"{field}: {msg}"},
    )


@app.post(
    "/signup", response_model=BaseResponse[TokenData], status_code=status.HTTP_200_OK
)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = find_user_by_email(db, user.email)

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(email=user.email, password=hash_password(user.password))

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.email})

    return {
        "success": True,
        "message": "User created successfully",
        "data": {
            "user_id": str(new_user.id),
            "access_token": token,
            "token_type": "bearer",
        },
    }


@app.post(
    "/login", response_model=BaseResponse[TokenData], status_code=status.HTTP_200_OK
)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = find_user_by_email(db, user.email)

    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = create_access_token({"sub": db_user.email})

    return BaseResponse(
        success=True,
        message="Login successful",
        data={
            "user_id": str(db_user.id),
            "access_token": token,
            "token_type": "bearer",
        },
    )


@app.post(
    "/forgot-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    user = find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    db.commit()
    send_email(user.email, otp)

    return {"message": "OTP sent to your email"}


@app.post(
    "/reset-password", response_model=BaseResponse[str], status_code=status.HTTP_200_OK
)
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    user = find_user_by_email(db, data.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check OTP
    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check expiry
    if not user.otp_expiry or datetime.utcnow() > user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP expired")

    # Update password
    user.password = hash_password(data.new_password)

    # Clear OTP
    user.otp = None
    user.otp_expiry = None

    db.commit()

    return {"message": "Password reset successful"}


@app.post(
    "/user-interests",
    response_model=BaseResponse[ProfileData],
    status_code=status.HTTP_201_CREATED,
)
def create_company_profile(data: CompanyProfileCreate, db: Session = Depends(get_db)):
    """
    Create or update user company profile (FULL PAYLOAD SUPPORT)
    """

    try:
        print("data --->>", data)

        # ✅ Store FULL payload dynamically
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

        # ✅ Check existing profile
        existing_entry = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.user_id == str(data.user_id))
            .first()
        )

        if existing_entry:
            # 🔄 UPDATE
            print(f"Updating profile for user {data.user_id}")
            existing_entry.data = profile_data
            db.commit()
            db.refresh(existing_entry)

            return {
                "success": True,
                "message": "Data updated successfully",
                "data": {
                    "id": str(existing_entry.id),
                    "user_id": str(existing_entry.user_id),
                    "data": existing_entry,
                },
            }

        else:
            # 🆕 CREATE
            print(f"Creating new profile for user {data.user_id}")
            new_entry = CompanyProfile(
                id=uuid4(), user_id=data.user_id, data=profile_data
            )
            db.add(new_entry)
            db.commit()
            db.refresh(new_entry)

            return {
                "success": True,
                "message": "Data saved successfully",
                "data": {
                    "id": str(new_entry.id),
                    "user_id": str(new_entry.user_id),
                    "data": new_entry,
                },
            }

    except Exception as e:
        db.rollback()
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


def handle_oauth_user_provisioning(
    db: Session, email: str
) -> BaseResponse[AuthTokenData]:
    """
    DRY Helper: Resolves an OAuth user by email, registers them if missing,
    generates a system JWT access token, and returns a unified response envelope.
    """
    # 1. Fetch or provision the user on-the-fly
    user = find_user_by_email(db, email)

    if not user:
        user = models.User(
            id=str(uuid4()),
            email=email,
            password=None,  # Explicitly NULL for passwordless OAuth accounts
            otp=None,
            otp_expiry=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Issue our standard system-wide access token
    backend_access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )

    # 3. Return the fully typed, unified response envelope
    return BaseResponse(
        success=True,
        message="Authentication successful",
        data=AuthTokenData(
            access_token=backend_access_token,
            token_type="bearer",
            user=UserData(id=str(user.id), email=user.email),
        ),
    )


@app.post(
    "/google",
    response_model=BaseResponse[AuthTokenData],
    status_code=status.HTTP_200_OK,
)
def google_authentication(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Receives the Google id_token from the frontend, validates it against Google,
    and delegates user provisioning and token generation to the shared authentication layer.
    """
    if not payload.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google ID token in request payload.",
        )

    try:
        id_info = id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        email = id_info.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token did not provide a valid email address.",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_41_UNAUTHORIZED,
            detail=f"Invalid Google credentials: {str(e)}",
        )

    return handle_oauth_user_provisioning(db, email)


@app.post(
    "/linkedin",
    response_model=BaseResponse[AuthTokenData],
    status_code=status.HTTP_200_OK,
)
def linkedin_authentication(
    payload: LinkedInAuthRequest, db: Session = Depends(get_db)
):
    """
    Receives the LinkedIn access_token from the frontend, validates it against
    LinkedIn's UserInfo API, and delegates user provisioning to the shared authentication layer.
    """
    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing LinkedIn access token in request payload.",
        )

    try:
        headers = {"Authorization": f"Bearer {payload.access_token}"}
        response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_41_UNAUTHORIZED,
                detail="Failed to verify token with LinkedIn or token has expired.",
            )

        user_info = response.json()
        email = user_info.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn profile does not contain a verified email address.",
            )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_41_UNAUTHORIZED,
            detail=f"LinkedIn authentication failed: {str(e)}",
        )

    return handle_oauth_user_provisioning(db, email)


@app.get(
    "/get-user-interests/{user_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
)
def get_user_interests(user_id: str, db: Session = Depends(get_db)):
    try:
        try:
            user_uuid = str(
                UUID(user_id)
            )  # ✅ validate AND convert to string immediately
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format.")

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

        # ✅ user_uuid is already a str now
        user = db.query(User).filter(User.id == user_uuid).first()

        if not user:
            return {
                "success": True,
                "message": "User not found",
                "data": {"user_id": user_id, "email": None, "profile": default_profile},
            }

        profile = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.user_id == user_uuid)  # ✅ also a str
            .first()
        )

        return {
            "success": True,
            "message": "Data not found" if not profile else "Data fetched successfully",
            "data": {
                "user_id": str(user.id),
                "email": user.email,
                "profile": profile.data if profile else default_profile,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get(
    "/get-user-id",
    response_model=BaseResponse[UserData],
    status_code=status.HTTP_200_OK,
)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "message": "User information retrieved successfully",
        "data": {"user_id": str(current_user.id), "email": current_user.email},
    }
