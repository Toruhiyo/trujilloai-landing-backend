import logging
from typing import Any
from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)

logger = logging.getLogger(__name__)


class AibiWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    # Public:

    # Protected:
    _additional_client_to_elevenlabs_filters = [
        lambda message: message.get("type") == "client_tool_result"
    ]

    # @client_tool_call(
    #     tool_name="go_to_section",
    #     required_parameters=["section", "question", "response", "language"],
    #     await_handler=False,
    # )
    # async def _handle_go_to_section_tool(self, message: dict[str, Any]):
    #     try:
    #         tool_call = message.get("client_tool_call", {})
    #         parameters = tool_call.get("parameters", {})
    #         logger.info(f"Go to section tool called with parameters: {parameters}")
    #     except Exception as e:
    #         logger.error(f"Error handling go to section tool: {e}")

    # Private:
