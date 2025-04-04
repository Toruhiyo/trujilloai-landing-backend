from fastapi import status
from src.app.demos.ai_bi.nlq.dtos import NlqResultDTO
from src.utils.typification.base_dto import BaseDTO


class NlqResponse(BaseDTO):
    message: str
    data: NlqResultDTO
    status_code: int = status.HTTP_200_OK
