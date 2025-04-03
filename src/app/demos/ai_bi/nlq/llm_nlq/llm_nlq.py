import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.exceptions import OutputParserException
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.runnables import chain

from src.app.demos.ai_bi.nlq.llm_nlq.dtos import NlqRequestDTO
from src.app.demos.ai_bi.nlq.llm_nlq.errors import (
    InvalidLLMResponseFormatError,
    UnsafeQueryError,
)
from src.config.vars_grabber import VariablesGrabber
from src.utils.json_toolbox import load_jsons_in_directory
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.langchain.llms.bedrock import BedrockLLM

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_PREFIX_FILEPATH = Path(__file__).parent / "prompting" / "prefix.txt"
DEFAULT_PROMPT_SUFFIX_FILEPATH = Path(__file__).parent / "prompting" / "suffix.txt"
DEFAULT_PROMPT_TEMPLATE_FILEPATH = (
    Path(__file__).parent / "prompting" / "examples-formatter.txt"
)
DEFAULT_EXAMPLES_FILEPATH = Path(__file__).parent / "prompting" / "examples"
DEFAULT_JSON_SCHEMA = json.loads(
    (Path(__file__).parent / "prompting" / "json-schema.json").read_text()
)

DEFAULT_MODEL_ID = (
    VariablesGrabber().get("DEMO_AIBI_NLQ_BEDROCK_INFERENCE_PROFILE_ID")
    or "us.meta.llama3-3-70b-instruct-v1:0"
)
DEFAULT_REGION = VariablesGrabber().get("AWS_REGION") or "us-east-1"

UNSAFE_OPERATIONS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


class AibiLlmTextToSQL(metaclass=DynamicSingleton):
    @property
    def model_id(self):
        return self.__model.model_id

    # Public:
    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        model_params: Optional[dict[str, Any]] = None,
        model_read_timeout: Optional[int] = None,
        prompt_prefix: str | Path = DEFAULT_PROMPT_PREFIX_FILEPATH,
        prompt_suffix: str | Path = DEFAULT_PROMPT_SUFFIX_FILEPATH,
        prompt_examples_formatter: str | Path = DEFAULT_PROMPT_TEMPLATE_FILEPATH,
        prompt_examples: list[dict] | Path = DEFAULT_EXAMPLES_FILEPATH,
        json_schema: Optional[dict[str, Any]] = DEFAULT_JSON_SCHEMA,
        region: str = DEFAULT_REGION,
    ):
        model_params = model_params or {}
        # Configure JSON schema if API supports it
        # model_params["response_format"] = {
        #     "type": "json_schema",
        #     "json_schema": json_schema,
        # }

        self.__create_prompt_template(
            prompt_prefix,
            prompt_suffix,
            prompt_examples_formatter,
            prompt_examples,
        )

        self.__model = BedrockLLM(
            model_id=model_id,
            params=model_params,
            region=region,
            read_timeout=model_read_timeout,
        )

    def compute(self, request: NlqRequestDTO) -> str:
        response = self.__compute_response(request)
        response = self.__validate_response(response)
        return response

    # Private:
    def __compute_response(self, request: NlqRequestDTO) -> str:
        llm_response = self.__execute_chain(request.natural_language_query)
        response = self.__extract_response(llm_response)
        return response

    def __execute_chain(self, natural_language_query: str) -> Any:
        chain = (
            self.__prompt_template
            | self.__model
            | self.__answer_transform_step
            # | self.__parser
        )

        try:
            response = chain.invoke(
                {
                    "natural_language_query": natural_language_query,
                }
            )
        except OutputParserException as e:
            logger.error(f"Failed to parse output: {type(e)}-{e}.")
            raise e

        return response

    def __extract_response(self, response: Any) -> str:
        try:
            if isinstance(response, list) and len(response) == 1:
                response = response[0]

            if isinstance(response, str):
                return response
        except Exception as e:
            raise InvalidLLMResponseFormatError(
                f"Failed to typify LLM response into NLQ response format: {type(e)}-{e}. Response: {response}"
            )

        raise InvalidLLMResponseFormatError(
            f"Failed to typify LLM response into NLQ response format: {type(response)}-{response}"
        )

    def __validate_response(self, response: str) -> str:
        # Check for unsafe SQL operations
        for pattern in UNSAFE_OPERATIONS:
            if re.search(pattern, response, re.IGNORECASE):
                raise UnsafeQueryError(
                    f"Query contains unsafe operation matching pattern: {pattern}"
                )

        return response

    @chain
    @staticmethod
    def __answer_transform_step(answer: str) -> str:
        # Remove code blocks if present
        if "```sql" in answer.lower():
            pattern = r"```(?:sql)?(.*?)```"
            matches = re.findall(pattern, answer, re.DOTALL)
            if matches:
                return matches[0].strip()

        # If the response directly starts with SELECT, assume it's a raw SQL query
        if answer.strip().upper().startswith("SELECT"):
            return json.dumps({"query": answer.strip()})

        return answer

    def __create_prompt_template(
        self,
        prompt_prefix: str | Path,
        prompt_suffix: str | Path,
        prompt_examples_formatter: str | Path,
        prompt_examples: list[dict] | Path,
    ):
        prompt_examples_formatter = (
            prompt_examples_formatter.read_text()
            if isinstance(prompt_examples_formatter, Path)
            else prompt_examples_formatter
        )

        prompt_prefix = (
            prompt_prefix.read_text()
            if isinstance(prompt_prefix, Path)
            else prompt_prefix
        )

        prompt_suffix = (
            prompt_suffix.read_text()
            if isinstance(prompt_suffix, Path)
            else prompt_suffix
        )

        examples = self.__load_prompt_examples(prompt_examples)

        example_prompt = PromptTemplate(
            template=prompt_examples_formatter,
            input_variables=[
                "example_id",
                "type",
                "natural_language_query",
                "sql_query",
            ],
        )

        self.__prompt_template = FewShotPromptTemplate(
            prefix=prompt_prefix,
            examples=examples,
            example_prompt=example_prompt,
            input_variables=["natural_language_query"],
            suffix=prompt_suffix,
        )

    def __load_prompt_examples(self, prompt_examples: list[dict] | Path):
        if isinstance(prompt_examples, Path):
            try:
                examples = load_jsons_in_directory(prompt_examples)
                return examples
            except Exception as e:
                logger.error(f"Failed to load prompt examples: {type(e)}-{e}")
                return []
        return prompt_examples
