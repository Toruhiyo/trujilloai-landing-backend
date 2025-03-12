from fastapi import status
from src.app.entities.messages.dtos import MessageDTO
from src.utils.typification.base_dto import BaseDTO


class SingleMessageResponse(BaseDTO):
    message: str
    data: MessageDTO
    status_code: int = status.HTTP_200_OK


class MultipleMessagesResponse(BaseDTO):
    message: str
    data: list[MessageDTO]
    status_code: int = status.HTTP_200_OK
