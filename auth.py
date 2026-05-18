from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import hashlib
import smtplib
import random
from email.mime.text import MIMEText

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT token creation
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


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
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email error:", e)
