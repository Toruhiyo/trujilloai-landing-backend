from services_utils.huggingface.bloom_toolbox import VariantType

from .abstract_llm_engine import AbstractLlmEngine
from .concrete_engines.bloom_engine import BloomEngine
from .concrete_engines.gpt3_engine import Gpt3Engine
from .concrete_engines.gpt_engine import GptEngine
from .concrete_engines.mock_engine import MockEngine
from .model_types import ModelType


class LlmEnginesFactory:
    # Public:
    @classmethod
    def create(cls, _type: ModelType, *args, **kwargs) -> AbstractLlmEngine:
        match _type:
            case ModelType.GPT3:
                return Gpt3Engine(*args, **kwargs)
            case ModelType.BLOOM:
                return BloomEngine(*args, **kwargs)
            # case ModelType.BLOOMZ:
            #     return BloomEngine(*args, variant=VariantType.BLOOMZ, **kwargs)
            case ModelType.GPT:
                return GptEngine(*args, **kwargs)
            case ModelType.MOCK:
                return MockEngine(*args, **kwargs)
            case _:
                raise NotImplementedError(f"Invalid text-structurer type {_type}.")
