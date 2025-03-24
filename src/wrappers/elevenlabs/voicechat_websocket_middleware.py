import logging
from typing import Any

from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)

logger = logging.getLogger(__name__)


class VoicechatWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    @client_tool_call(tool_name="highlight_text")
    async def handle_search_tool(self, message: dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            logger.info(f"Highlight text tool called with parameters: {parameters}")

        except Exception as e:
            logger.error(f"Error handling search tool: {e}")
