import logging

from services_utils.huggingface.bloom_toolbox import count_tokens

from ..abstract_llm_engine import AbstractLlmEngine
from ..model_types import ModelType

logger = logging.getLogger(__name__)


class MockEngine(AbstractLlmEngine):
    # Public:
    @property
    def type(self) -> ModelType:
        return ModelType.MOCK

    # Protected:
    @property
    def _max_model_tokens(self) -> int:
        return 1000

    def _execute_text_completion(self, *args, **kwargs) -> str:
        return kwargs.get("mock_reply") or "{}"

    def _count_tokens(self, prompt: str) -> int:
        variant = self._engine_params.get("variant")
        return count_tokens(prompt, variant=variant)

    # Private:
