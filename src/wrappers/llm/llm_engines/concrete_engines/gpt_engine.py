import logging

from services_utils.openai.chatgpt_toolbox import chat_completion, count_tokens

from ..abstract_llm_engine import AbstractLlmEngine
from ..errors import StoppedByLength
from ..model_types import ModelType

logger = logging.getLogger(__name__)


class GptEngine(AbstractLlmEngine):
    # Public:
    @property
    def type(self) -> ModelType:
        return self.__model_type

    @property
    def model(self) -> str:
        return self.__model

    def __init__(
        self,
        *args,
        model_type: ModelType = ModelType.GPT,
        model: str = "gpt-3.5-turbo",
        **kwargs,
    ) -> None:
        self.__model_type = model_type
        self.__model = model
        super().__init__(*args, **kwargs)

    # Protected:
    @property
    def _max_model_tokens(self) -> int:
        # !! make this a JSON file !! #
        match self.model:
            case "gpt-3.5-turbo":
                return 4096
            case "gpt-3.5-turbo-16k-0613":
                return 16384
            case "gpt-4":
                return 8192
            case _:
                raise ValueError(f"Unsupported model type: {self.type}")

    def _execute_text_completion(self, prompt: str, **kwargs) -> str:
        reply, reason = chat_completion(prompt, model=self.__model, **kwargs)
        match reason:
            case "stop":
                return reply
            case "length":
                raise StoppedByLength(
                    f'ChatGPTEngine reply stopped by reason "{reason}". Reply: {reply}'
                )
            case _:
                raise ValueError(f"Unexpected reason: {reason}. Reply: {reply}")

    def _count_tokens(self, prompt: str) -> int:
        return count_tokens(prompt)

    # Private:
