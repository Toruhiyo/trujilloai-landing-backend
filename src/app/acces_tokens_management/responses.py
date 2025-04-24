from typing import Literal
from fastapi import status
from src.app.common.response import BooleanResponse


class AccessTokenResponse(BooleanResponse):
    message: str = "Access token generated successfully"
    data: dict[Literal["access_token"], str]
    status_code: int = status.HTTP_200_OK
