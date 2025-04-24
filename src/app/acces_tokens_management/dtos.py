from datetime import datetime

from src.utils.typification.base_dto import BaseDTO


class AccessToken(BaseDTO):
    token: str
    expires_at: datetime
