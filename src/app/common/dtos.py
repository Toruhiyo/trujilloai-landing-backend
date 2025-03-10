from typing import Optional
from src.utils.typification.base_dto import BaseDTO
from .enums import NotificationLevel


class NotificationDTO(BaseDTO):
    level: NotificationLevel
    message: str
    mask_id: Optional[int] = None
    occurrence_id: Optional[int] = None


class ErrorDTO(BaseDTO):
    type: str
    message: str


class KeyValuePairDTO(BaseDTO):
    key: str
    value: str
