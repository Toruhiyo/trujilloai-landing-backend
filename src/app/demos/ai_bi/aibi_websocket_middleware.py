import logging
from typing import Any, Optional, Dict

from src.app.demos.ai_bi.nlq.dtos import NlqResultDTO
from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)
from src.app.demos.ai_bi.nlq.nlq_agent import AibiNlqAgent

logger = logging.getLogger(__name__)


class AibiWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    # Public:

    # Protected:
    _additional_client_to_elevenlabs_filters = [
        lambda message: message.get("type") == "client_tool_result"
    ]

    @client_tool_call(
        tool_name="query_database_from_text",
        required_parameters=["user_query"],
        await_handler=False,
        send_results_to_elevenlabs=True,
        send_results_to_client=True,
    )
    async def _handle_nlq_tool(
        self, message: dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        tool_call = message.get("client_tool_call", {})
        parameters = tool_call.get("parameters", {})
        logger.info(f"Database query tool called with parameters: {parameters}")

        user_query = parameters.get("user_query", "")
        title = parameters.get("title", "")
        if not user_query:
            raise ValueError("user_query parameter is required")

        nlq_result = self.__compute_nlq_result(user_query)
        nlq_result.title = title

        return nlq_result.model_dump()

    # Private:
    def __compute_nlq_result(self, user_query: str) -> NlqResultDTO:
        nlq_agent = AibiNlqAgent()
        result = nlq_agent.compute(user_query)
        return result
