from text_utils.regex_toolbox import get_first_json

from src.wrappers.llm.llm_engines.errors import FailedExtractingData
from src.wrappers.llm.llm_engines.llm_engines_factory import LlmEnginesFactory
from src.wrappers.llm.llm_engines.model_types import ModelType


class LlmTextStructurer:
    # Public:
    def __init__(self, model_type: ModelType = ModelType.GPT, **kwargs):
        self.__llm_engine = LlmEnginesFactory.create(model_type, **kwargs)

    def compute(self, prompt: str) -> list | dict:
        reply = self.__llm_engine.compute(prompt)
        data = self.__extract_json_from_reply(reply)
        return data

    # Private:
    def __extract_json_from_reply(self, reply: str) -> list | dict:
        try:
            output = get_first_json(reply)
        except Exception as e:
            raise FailedExtractingData(
                f'Failed extracting JSON type data from "{reply}". Details: "{type(e)}-{e}".'
            ) from e
        if not isinstance(output, (list, dict)):
            raise FailedExtractingData(
                f'Failed extracting JSON type data from "{reply}".'
            )
        return output
        # output = get_first_json(reply)
        # if isinstance(output, dict):
        #     output = [output]
        # if isinstance(output, list) and len(output) > 0:
        #     if all(map(lambda e: isinstance(e, dict), output)):
        #         return output
        # raise FailedExtractingData(f'Failed extracting JSON type data from "{reply}".')
