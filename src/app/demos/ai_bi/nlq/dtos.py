from typing import Any, Optional
from src.utils.typification.base_dto import BaseDTO


class SqlResultDTO(BaseDTO):
    columns: list[str]
    rows: list[list[Any]]
    query: str
    execution_time_ms: float


class NlqResultDTO(BaseDTO):
    natural_language_query: str
    sql_query: str
    result: SqlResultDTO
    execution_time_ms: float
    title: Optional[str] = None
