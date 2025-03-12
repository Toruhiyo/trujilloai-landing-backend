from datetime import datetime
from typing import Optional
from src.app.entities.messages.enums import RoleType
from src.utils.typification.base_dto import BaseDTO


class MessageDTO(BaseDTO):
    # id: str
    conversation_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[RoleType] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    content: str
