from uuid import uuid4

from sqlalchemy import CHAR, JSON, Column, ForeignKey
from sqlalchemy.orm import relationship

from core.database import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    user_id = Column(CHAR(36), ForeignKey("users2.id"), unique=True, nullable=False)
    data = Column(JSON, nullable=False)

    user = relationship("User")
