from typing import Optional, Dict, Any

from src.app.demos.ai_bi.nlq.enums import ChartType
from src.utils.typification.base_dto import BaseDTO


class NlqRequestDTO(BaseDTO):
    natural_language_query: str
    metadata: Optional[Dict[str, Any]] = None


class NlqLlmResultsDTO(BaseDTO):
    sql_queries: list[str]
    title: Optional[str] = None
    chart_type: Optional[ChartType] = None
