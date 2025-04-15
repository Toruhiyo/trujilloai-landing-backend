import json
import logging
import os
from pathlib import Path
from random import shuffle
import re
from typing import Any, Callable, Optional

from src.app.landing.enums import SectionName
from src.app.landing_voicechat.highlighting.dtos import HighlightedTextDTO
from src.config.vars_grabber import VariablesGrabber
from src.utils.dict_toolbox import (
    remove_other_keys_from_dict_list,
    remove_other_keys_from_dict,
)
from src.utils.list_toolbox import flatten_list
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.langchain.llms.bedrock import BedrockLLM

from .errors import (
    InvalidLLMResponseFormatError,
    InvalidPromptTemplateError,
)
from langchain_core.runnables import chain
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from src.utils.json_toolbox import load_jsons_in_directory, make_serializable


DEFAULT_PROMPT_TEMPLATE_FILEPATH = (
    Path(__file__).parent / "prompting" / "examples-formatter.txt"
)
DEFAULT_EXAMPLES_FILEPATH = Path(__file__).parent / "prompting" / "examples"
DEFAULT_PROMPT_PREFIX_FILEPATH = Path(__file__).parent / "prompting" / "prefix.txt"
DEFAULT_PROMPT_SUFFIX_FILEPATH = Path(__file__).parent / "prompting" / "suffix.txt"

SHALL_EXPORT_LOGS = os.environ.get("IS_LOCAL", "False").lower() == "true"

LOGS_DIRECTORY = Path("logs")

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = (
    VariablesGrabber().get("AWS_BEDROCK_MODEL_ID") or "meta.llama3-3-70b-instruct-v1:0"
)

DEFAULT_JSON_SCHEMA = json.loads(
    (Path(__file__).parent / "prompting" / "json-schema.json").read_text()
)

DEFAULT_REGION = VariablesGrabber().get("AWS_REGION") or "us-east-1"


class LlmTextHighlighter(metaclass=DynamicSingleton):

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
        # !! Json shcema only available for APi versions 2024-08-01-preview and later. !!
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
        self.__parser = JsonOutputParser()

    def compute(
        self,
        question: str,
        answer: str,
        section_content: str,
    ) -> HighlightedTextDTO:
        results = self.__compute_results(question, answer, section_content)
        results = self.__correct_results(results)
        return results

    # Private:
    def __compute_results(
        self, question: str, answer: str, section_content: str
    ) -> HighlightedTextDTO:
        response = self.__execute_chain(question, answer, section_content)
        results = self.__extract_results(response)
        return results

    def __execute_chain(self, question: str, answer: str, section_content: str) -> Any:
        chain = (
            self.__prompt_template
            | self.__model
            | self.__answer_transform_step
            | self.__parser
        )
        if SHALL_EXPORT_LOGS:
            try:
                self.__export_prompt_log(question, answer, section_content)
            except Exception as e:
                logger.warning(f"Failed to export prompt log: {type(e)}-{e}.")
        try:
            response = chain.invoke(
                (
                    {
                        "question": question,
                        "answer": answer,
                        "section_content": section_content,
                    }
                )
            )
        except OutputParserException as e:
            logger.error(f"Failed to parse output: {type(e)}-{e}.")
            raise e
        if SHALL_EXPORT_LOGS:
            try:
                self.__export_reply_log(
                    response,
                    question,
                    answer,
                    section_content,
                )
            except Exception as e:
                logger.warning(f"Failed to export reply log: {type(e)}-{e}.")
        return response

    def __extract_results(self, answer: Any) -> HighlightedTextDTO:
        try:
            if isinstance(answer, list):
                if len(answer) == 1:
                    answer = answer[0]
            if isinstance(answer, dict):
                results = HighlightedTextDTO(**answer)
            else:
                raise ValueError(f"Unexpected response type: {type(answer)}")
        except Exception as e:
            raise InvalidLLMResponseFormatError(
                f"Failed to typify LLM response into Partially Accepted results format: {type(e)}-{e}. Response: {answer}"
            )
        return results

    def __correct_results(self, results: HighlightedTextDTO) -> HighlightedTextDTO:
        return results

    @chain
    @staticmethod
    def __answer_transform_step(answer: str) -> str:
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
                "question",
                "answer",
                "section_content",
                "results",
            ],
        )
        try:
            self.__prompt_template = FewShotPromptTemplate(
                prefix=prompt_prefix,
                examples=examples,
                example_prompt=example_prompt,
                input_variables=[
                    "question",
                    "answer",
                    "section_content",
                ],
                suffix=prompt_suffix,
            )
        except Exception as e:
            raise InvalidPromptTemplateError(
                f"Failed to create prompt template: {type(e)}-{e}"
            )

    @classmethod
    def __load_prompt_examples(
        cls, examples: list[dict] | Path
    ) -> list[dict[str, str]]:
        examples = (
            load_jsons_in_directory(examples, encoding="utf-8")
            if isinstance(examples, Path)
            else examples
        )
        if not isinstance(examples, list) or not all(
            isinstance(example, dict) for example in examples
        ):
            raise InvalidPromptTemplateError(
                "Invalid examples format. Expected a list of dictionaries."
            )
        shuffle(examples)
        examples = [d | {"example_id": i + 1} for i, d in enumerate(examples)]
        examples = [d | {"type": d.get("type", "CORRECT")} for d in examples]
        examples = [
            {
                k: json.dumps(v, ensure_ascii=False)
                .replace("{", "{{")
                .replace("}", "}}")
                for k, v in example.items()
            }
            for example in examples
        ]
        return examples

    def __export_prompt_log(
        self,
        question: str,
        answer: str,
        section_content: str,
    ):
        prompt = self.__prompt_template.format(
            question=question,
            answer=answer,
            section_content=section_content,
        )
        if not LOGS_DIRECTORY.exists():
            LOGS_DIRECTORY.mkdir()
        last_prompt_filepath = LOGS_DIRECTORY / f"{type(self).__name__}-last-prompt.txt"
        last_prompt_filepath.write_text(prompt, encoding="utf-8")

    def __export_reply_log(
        self,
        response: Any,
        question: str,
        answer: str,
        section_content: str,
    ):
        if not LOGS_DIRECTORY.exists():
            LOGS_DIRECTORY.mkdir()
        last_reply_filepath = LOGS_DIRECTORY / f"{type(self).__name__}-last-reply.json"
        try:
            last_reply_filepath.write_text(
                json.dumps(
                    make_serializable(
                        {
                            "INPUT": {
                                "question": question,
                                "answer": answer,
                                "section_content": section_content,
                            },
                            "OUTPUT": response,
                        }
                    ),
                    indent=4,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            last_reply_filepath.write_text(str(response))
