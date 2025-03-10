import logging
from pathlib import Path
from time import perf_counter
from typing import Optional

from .caching.cache_manager import CacheManager
from .errors import ExceededMaxLength, TextCompletionFailed
from .model_types import ModelType

logger = logging.getLogger(__name__)


CHAR_2_TOKENS_FACTOR = 0.25
TOKENS_RATIO_LAZY_ESTIMATION_THRESHOLD = 0.5


class AbstractLlmEngine:
    # Public:
    @property
    def type(self) -> ModelType:
        raise NotImplementedError("Abstract property.")

    def __str__(self) -> str:
        return str(self.type)

    def __init__(
        self,
        max_input_tokens: Optional[int] = None,
        min_input_tokens: int = 50,
        prompt_log_level: Optional[int] = logging.DEBUG,
        prompt_output_inject_text: Optional[str] = None,
        cache_directory: Optional[Path] = None,
        version_name: str = "undefined",
        **kwargs,
    ) -> None:
        if max_input_tokens is not None and max_input_tokens > self._max_model_tokens:
            raise ValueError(
                f"max_input_tokens ({max_input_tokens}) cannot be larger than the model's max tokens ({self._max_model_tokens})"
            )
        self.__max_input_tokens = max_input_tokens or self._max_model_tokens
        self.__min_input_tokens = min_input_tokens
        self.__prompt_log_level = prompt_log_level
        self.__prompt_output_inject_text = prompt_output_inject_text
        self._engine_params = kwargs
        self.__cache_manager = (
            CacheManager(cache_directory, version_name=version_name)
            if isinstance(cache_directory, Path)
            else None
        )

    def compute(
        self,
        prompt: str,
        max_input_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        self._execute_text_completion_kwargs = kwargs
        max_input_tokens = max_input_tokens or self.__max_input_tokens
        n_tokens = self._count_tokens(prompt)
        if n_tokens > max_input_tokens:
            raise ExceededMaxLength(
                n_tokens=n_tokens,
                max_input_tokens=max_input_tokens,
            )
        if n_tokens < self.__min_input_tokens:
            raise ValueError(
                f"Input text must be at least {self.__min_input_tokens} tokens long."
            )
        logger.debug(f"Starting to execute {self}...")
        t0 = perf_counter()
        reply = self.__execute_model(prompt)
        logger.debug(
            f"Finished executing {self}. Elapsed time: {perf_counter() - t0:.2f} seconds."
        )
        return reply

    # Protected:
    @property
    def _max_model_tokens(self) -> int:
        raise NotImplementedError(
            "This property cannot be called from Abstract class. Must be overwritten by child class."
        )

    def _execute_text_completion(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("Abstract method.")

    def _compute_tokens(
        self, prompt: str, max_length: Optional[int] = None, must_be_exact: bool = False
    ) -> int:
        max_length = max_length or self._max_model_tokens
        if not must_be_exact:
            estimate = self._estimate_tokens(prompt)
            if (
                abs(estimate - max_length)
                > TOKENS_RATIO_LAZY_ESTIMATION_THRESHOLD * max_length
            ):
                return estimate
        return self._count_tokens(prompt)

    def _count_tokens(self, prompt: str) -> int:
        raise NotImplementedError("Abstract method.")

    def _estimate_tokens(self, prompt: str) -> int:
        return int(len(prompt) * CHAR_2_TOKENS_FACTOR)

    # Private:
    def __execute_model(self, prompt: str) -> str:
        logger.log(
            self.__prompt_log_level, f"{self} - PROMPT: {prompt}"
        ) if self.__prompt_log_level else None
        try:
            reply = self.__complete_text(prompt, **self._execute_text_completion_kwargs)
        except Exception as e:
            raise TextCompletionFailed(
                f'Failed executing {self.type}: "{type(e)}: {e}".'
            )
        logger.log(
            self.__prompt_log_level, f"{self} - REPLY: {reply}"
        ) if self.__prompt_log_level else None
        if isinstance(self.__prompt_output_inject_text, str):
            reply = f"{self.__prompt_output_inject_text}{reply}"
        return reply

    def __complete_text(self, prompt: str, **kwargs) -> str:
        if not self.__cache_manager:
            return self._execute_text_completion(prompt, **kwargs)
        return self.__cache_manager.get_or_set(
            prompt, lambda: self._execute_text_completion(prompt, **kwargs)
        )
