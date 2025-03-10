from typing import Optional

from fastapi import status
from pydantic import Field

from src.app.generic_dtos import BaseDTO


class BadRequestError(BaseDTO):
    message: str = Field(..., description="Short description of the error")
    data: Optional[dict] = Field(
        default=None, description="Additional data about the error"
    )
    status_code: Optional[int] = status.HTTP_400_BAD_REQUEST


class ErrorResponse(BaseDTO):
    message: str = Field(..., description="Short description of the error")
    data: Optional[dict] = Field(
        default=None, description="Additional data about the error"
    )
    status_code: Optional[int] = status.HTTP_200_OK


class DeleteResponse(BaseDTO):
    message: str
    status_code: int = status.HTTP_204_NO_CONTENT
