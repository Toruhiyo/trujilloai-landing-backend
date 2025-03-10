from datetime import datetime
from src.utils.typification.base_dto import BaseDTO


class UserInputDTO(BaseDTO):
    username: str
    email: str


class UserDTO(BaseDTO):
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    enabled: bool
