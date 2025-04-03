from typing import Optional, Dict, List, Any

from src.utils.typification.base_dto import BaseDTO


class SqlResultDTO(BaseDTO):
    columns: List[str]
    rows: List[List[Any]]
    query: str
    execution_time_ms: float
