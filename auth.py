import hashlib
import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT token creation
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# JWT token verification
def verify_token(token: str) -> dict | None:
    """
    Verifies a JWT token and returns the payload if valid, otherwise returns None.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def preprocess_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str):
    password = preprocess_password(password)
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    plain = preprocess_password(plain)
    return pwd_context.verify(plain, hashed)


# Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))


# Send Email
def send_email(to_email, otp):
    subject = "Password Reset OTP"
    body = f"Your OTP is: {otp}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
        server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email error:", e)
