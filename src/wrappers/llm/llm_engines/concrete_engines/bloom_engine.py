import logging

from services_utils.huggingface.bloom_toolbox import (
    count_tokens,
    get_error_message,
    get_max_model_tokens_from_exception,
    get_n_tokens_from_exception,
    text_completion,
)

from ..abstract_llm_engine import AbstractLlmEngine, ExceededMaxLength
from ..errors import InvalidRequest
from ..model_types import ModelType

logger = logging.getLogger(__name__)


class BloomEngine(AbstractLlmEngine):
    # Public:
    @property
    def type(self) -> ModelType:
        return ModelType.BLOOM

    # Protected:
    @property
    def _max_model_tokens(self) -> int:
        return 1000

    def _execute_text_completion(self, prompt: str) -> str:
        try:
            return text_completion(prompt, **self._engine_params)
        except Exception as e:
            msg = str(e)
            if msg.startswith("Error 422:"):
                # raise ExceededMaxLength(n_tokens=1878, max_tokens=1000) from e
                n_tokens = get_n_tokens_from_exception(e)
                max_tokens = get_max_model_tokens_from_exception(e)
                raise ExceededMaxLength(
                    original_exception=e, n_tokens=n_tokens, max_tokens=max_tokens
                ) from e
            if msg.startswith("Error 400:"):
                msg = get_error_message(e)
                raise InvalidRequest(msg, original_exception=e) from e
            raise e

    def _count_tokens(self, prompt: str) -> int:
        variant = self._engine_params.get("variant")
        return count_tokens(prompt, variant=variant)

    # Private:
