from typing import Optional, Dict, Any

from src.utils.typification.base_dto import BaseDTO


class NlqRequestDTO(BaseDTO):
    natural_language_query: str
    metadata: Optional[Dict[str, Any]] = None
