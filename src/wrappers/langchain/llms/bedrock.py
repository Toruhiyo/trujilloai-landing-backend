import logging
from math import ceil
from time import perf_counter
from typing import Any, Dict, Iterator, List, Mapping, Optional

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from pydantic import Extra

from src.wrappers.aws.bedrock_model import BedrockWrapper

logger = logging.getLogger(__name__)


class BedrockLLM(LLM):
    """A custom chat model that echoes the first `n` characters of the input.

    When contributing an implementation to LangChain, carefully document
    the model including the initialization parameters, include
    an example of how to initialize the model and include any relevant
    links to the underlying models documentation or API.

    Example:

        .. code-block:: python

            model = CustomChatModel(n=2)
            result = model.invoke([HumanMessage(content="hello")])
            result = model.batch([[HumanMessage(content="hello")],
                                 [HumanMessage(content="world")]])
    """

    # n: int
    """The number of characters from the last message of the prompt to be echoed."""

    class Config:
        extra = Extra.allow

    def __init__(
        self,
        model_id: str,
        region: str,
        *args,
        params: Optional[dict[str, Any]] = None,
        read_timeout: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.__model_id = model_id
        self.__region = region
        self.__params = params
        self.__read_timeout = read_timeout

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(
            f"Calling Bedrock model ({self.__model_id}) with a prompt of {len(prompt)} characters (~{ceil(len(prompt)/4)} tokens)."
        )
        t0 = perf_counter()
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        response = BedrockWrapper(
            region=self.__region, read_timeout=self.__read_timeout
        ).invoke_model(
            self.__model_id,
            prompt,
            params=self.__params,
        )
        logger.info(
            f"Bedrock model ({self.__model_id}) call took {perf_counter() - t0:.2f} seconds."
        )
        answer = None
        if "generation" in response:
            answer = response["generation"]
        elif "outputs" in response:
            answer = response["outputs"][0]["text"]
        elif "content" in response:
            answer = response["content"][0]["text"]
        else:
            raise NotImplementedError(f"Unexpected response: {response}")
        if answer is None:
            raise ValueError(f"Failed to extract answer from response: {response}")
        return answer

    @property
    def model_id(self) -> str:
        return self.__model_id

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return a dictionary of identifying parameters."""
        return {
            "model_name": self.__model_id,
            "model_parameters": self.__params,
        }

    @property
    def _llm_type(self) -> str:
        return "AWS Bedrock"
