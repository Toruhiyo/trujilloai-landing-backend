from typing import Any, Optional
from src.utils.typification.base_dto import BaseDTO
from src.app.demos.ai_bi.nlq.enums import Unit, ChartType


class SqlResultDTO(BaseDTO):
    columns: list[str]
    rows: list[list[Any]]
    query: str
    execution_time_ms: float
    columns_units: Optional[list[Unit | None]] = None


class NlqResultDTO(BaseDTO):
    natural_language_query: str
    results: list[SqlResultDTO]
    chart_type: Optional[ChartType] = None
    total_time_ms: float
    generation_time_ms: float
    title: Optional[str] = None
