import logging
from typing import Any, Dict

from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)

logger = logging.getLogger(__name__)


class VoicechatWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    @client_tool_call(tool_name="highlight_text")
    async def handle_search_tool(self, message: Dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            go_to_section_message = {
                "client_tool_call": {
                    "tool_name": "go_to_section",
                    "tool_call_id": tool_call.get("tool_call_id"),
                    "parameters": parameters,
                },
                "type": "client_tool_call",
            }
            await self.send_message_to_client(go_to_section_message)

        except Exception as e:
            logger.error(f"Error handling search tool: {e}")
