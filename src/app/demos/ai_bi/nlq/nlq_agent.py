import logging
from typing import Optional

from src.app.demos.ai_bi.nlq.dtos import SqlResultDTO
from src.app.demos.ai_bi.nlq.llm_nlq.dtos import NlqRequestDTO
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

    def compute(self, natural_language_query: str) -> SqlResultDTO:
        sql_query = self.__compute_sql_query(natural_language_query)
        sql_result = self.__execute_sql_query(sql_query)
        return sql_result

    # Private:
    def __compute_sql_query(self, natural_language_query: str) -> str:
        nlq_request = NlqRequestDTO(natural_language_query=natural_language_query)
        return self.__llm_text_to_sql.compute(nlq_request)

    def __execute_sql_query(self, query: str) -> SqlResultDTO:
        return self.__query_executor.execute(query)
