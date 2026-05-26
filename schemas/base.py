from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with shared configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
    )


class BaseResponse(BaseSchema, Generic[T]):
    """Standardized top-level API envelope structure for all responses."""

    success: bool = True
    message: str
    data: Optional[T] = None
