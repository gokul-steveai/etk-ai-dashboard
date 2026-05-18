import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR, JSON
from database import Base


class User(Base):
    __tablename__ = "users2"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    otp = Column(String(10), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = Column(CHAR(36), ForeignKey("users2.id"), unique=True, nullable=False)
    data = Column(JSON, nullable=False)

    user = relationship("User")
