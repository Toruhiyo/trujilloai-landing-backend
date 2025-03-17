from src.utils.typification.base_dto import BaseDTO
from typing import Literal
from datetime import datetime
from src.app.entities.messages.enums import RoleType
from pydantic import Field


class InputMessageDTO(BaseDTO):
    content: str


class ChatbotBotMessageDTO(BaseDTO):
    content: str
    conversation_id: str
    role: RoleType = Field(default=RoleType.ASSISTANT)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class HighlightRequestDTO(BaseDTO):
    text: str
    section: Literal[
        "HERO",
        "SERVICES",
        "WHY_CHOOSE_ORIOL",
        "HOW_SOLO_OR_SQUAD",
        "HOW_METHODOLOGY",
        "SELECTED_PROJECTS",
        "BIO",
        "CONTACT_FORM",
    ]
