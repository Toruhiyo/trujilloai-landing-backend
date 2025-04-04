import logging
from typing import Any
from uuid import uuid5, NAMESPACE_URL

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
    )
    async def _handle_nlq_tool(self, message: dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            logger.info(f"Database query tool called with parameters: {parameters}")

            user_query = parameters.get("user_query", "")
            if not user_query:
                raise ValueError("user_query parameter is required")

            nlq_result = self.__compute_nlq_result(user_query)

            tool_call_id = tool_call.get("tool_call_id", "")
            tool_call_uuid = (
                tool_call_id.split("_")[-1]
                if tool_call_id
                else str(uuid5(NAMESPACE_URL, "database_query"))
            )

            await self.send_message_to_client(
                {
                    "type": "client_tool_call",
                    "client_tool_call": {
                        "tool_name": "query_database_from_text_result",
                        "tool_call_id": f"query_database_from_text_result_{tool_call_uuid}",
                        "parameters": nlq_result.model_dump(),
                    },
                }
            )
        except Exception as e:
            error_message = f"Error processing natural language query: {str(e)}"
            logger.error(error_message)

    # Private:
    def __compute_nlq_result(self, user_query: str) -> NlqResultDTO:
        nlq_agent = AibiNlqAgent()
        result = nlq_agent.compute(user_query)
        return result
