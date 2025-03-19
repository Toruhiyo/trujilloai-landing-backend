from typing import Optional
from fastapi import status
from src.utils.typification.base_dto import BaseDTO


class SingleBasicResponse(BaseDTO):
    message: str
    data: Optional[dict] = None
    status_code: int = status.HTTP_200_OK
