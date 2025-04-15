from typing import Optional

from src.app.landing.enums import LanguageCode, SectionName
from src.utils.typification.base_dto import BaseDTO


class HighlightedTextDTO(BaseDTO):
    texts: list[str]
    section: Optional[SectionName] = None
    language: Optional[LanguageCode] = None
