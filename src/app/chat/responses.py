from fastapi import status
from src.utils.typification.base_dto import BaseDTO


class HighlightTextResponseDTO(BaseDTO):
    message: str
    data: str
    status_code: int = status.HTTP_200_OK
