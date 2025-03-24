import logging
from typing import Any, Dict

from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)

logger = logging.getLogger(__name__)


class VoicechatWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    @client_tool_call(tool_name="go_to_section")
    def handle_search_tool(self, message: Dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            query = parameters.get("query")

            if query:
                logger.info(f"Client requested search for: {query}")
                # Implement search logic here

        except Exception as e:
            logger.error(f"Error handling search tool: {e}")
