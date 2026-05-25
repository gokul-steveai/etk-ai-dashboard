from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standardized top-level API envelope structure for all responses."""

    success: bool = True
    message: str
    data: Optional[T] = None
