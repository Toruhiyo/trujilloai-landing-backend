from fastapi import status

from src.app.generic_dtos import BaseDTO
from src.app.entities.users.dtos import UserDTO


class MultipleUserResponse(BaseDTO):
    message: str
    data: list[UserDTO]
    status_code: int = status.HTTP_200_OK


class SingleUserResponse(BaseDTO):
    message: str
    data: UserDTO
    status_code: int = status.HTTP_200_OK


class SingleUserUpdateResponse(BaseDTO):
    message: str
    data: UserDTO
    status_code: int = status.HTTP_200_OK
