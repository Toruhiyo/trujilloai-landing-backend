import logging
from time import perf_counter
from typing import Optional

from src.app.demos.ai_bi.nlq.dtos import NlqResultDTO, SqlResultDTO
from src.app.demos.ai_bi.nlq.llm_nlq.dtos import NlqLlmResultsDTO, NlqRequestDTO
from src.app.demos.ai_bi.nlq.llm_nlq.llm_nlq import AibiLlmTextToSQL
from src.app.demos.ai_bi.nlq.query_executor import AibiQueryExecutor
from src.app.demos.ai_bi.nlq.units_assignation.column_units_assigner import (
    ColumnUnitsAssigner,
)
from src.utils.decorators import retry
from src.utils.metaclasses import DynamicSingleton

logger = logging.getLogger(__name__)


class AibiNlqAgent(metaclass=DynamicSingleton):
    # Public:
    def __init__(
        self,
        llm_text_to_sql: Optional[AibiLlmTextToSQL] = None,
        query_executor: Optional[AibiQueryExecutor] = None,
    ):
        self.__llm_text_to_sql = llm_text_to_sql or AibiLlmTextToSQL()
        self.__query_executor = query_executor or AibiQueryExecutor()

    def compute(self, natural_language_query: str) -> NlqResultDTO:
        t0 = perf_counter()
        llm_results, sql_results, generation_time_ms = self.__compute_results(
            natural_language_query
        )
        total_time = (perf_counter() - t0) * 1000
        return NlqResultDTO(
            natural_language_query=natural_language_query,
            title=llm_results.title,
            results=sql_results,
            total_time_ms=total_time,
            generation_time_ms=generation_time_ms,
        )

    # Private:
    @retry(max_retries=5, delay=0)
    def __compute_results(
        self, natural_language_query: str
    ) -> tuple[NlqLlmResultsDTO, list[SqlResultDTO], float]:
        llm_results, generation_time_ms = self.__compute_sql_query(
            natural_language_query
        )
        sql_results = [
            self.__execute_sql_query(sql_query) for sql_query in llm_results.sql_queries
        ]
        sql_results = [
            self.__assign_column_units(sql_result) for sql_result in sql_results
        ]
        return llm_results, sql_results, generation_time_ms

    def __compute_sql_query(
        self, natural_language_query: str
    ) -> tuple[NlqLlmResultsDTO, float]:
        t0 = perf_counter()
        nlq_request = NlqRequestDTO(natural_language_query=natural_language_query)
        sql_result = self.__llm_text_to_sql.compute(nlq_request)
        dt = perf_counter() - t0
        return sql_result, dt

    def __execute_sql_query(self, query: str) -> SqlResultDTO:
        return self.__query_executor.execute(query)

    def __assign_column_units(self, sql_result: SqlResultDTO) -> SqlResultDTO:
        columns_units = ColumnUnitsAssigner().compute(sql_result.columns)
        sql_result.columns_units = columns_units
        return sql_result
