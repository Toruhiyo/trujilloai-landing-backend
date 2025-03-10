import logging

from services_utils.openai.gpt3_toolbox import count_tokens, text_completion

from ..abstract_llm_engine import AbstractLlmEngine
from ..model_types import ModelType

logger = logging.getLogger(__name__)


class Gpt3Engine(AbstractLlmEngine):
    # Public:
    @property
    def type(self) -> ModelType:
        return ModelType.GPT3

    # Protected:
    @property
    def _max_model_tokens(self) -> int:
        return 3000

    def _execute_text_completion(self, prompt: str) -> str:
        return text_completion(prompt, **self._engine_params)

    def _count_tokens(self, prompt: str) -> int:
        return count_tokens(prompt)

    # Private:
