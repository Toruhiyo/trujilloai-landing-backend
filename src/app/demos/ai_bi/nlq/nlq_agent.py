import logging
from time import perf_counter
from typing import Optional

from src.app.demos.ai_bi.nlq.dtos import NlqResultDTO, SqlResultDTO
from src.app.demos.ai_bi.nlq.llm_nlq.dtos import NlqLlmResultsDTO, NlqRequestDTO
from src.app.demos.ai_bi.nlq.llm_nlq.llm_nlq import AibiLlmTextToSQL
from src.app.demos.ai_bi.nlq.query_executor import AibiQueryExecutor
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
        llm_results, generation_time_ms = self.__compute_sql_query(
            natural_language_query
        )
        sql_result = self.__execute_sql_query(llm_results.sql_query)
        return NlqResultDTO(
            natural_language_query=natural_language_query,
            sql_query=llm_results.sql_query,
            title=llm_results.title,
            result=sql_result,
            execution_time_ms=generation_time_ms + sql_result.execution_time_ms,
        )

    # Private:
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
