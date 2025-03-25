import logging
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from src.app.voicechat.highlighting.text_highligther import TextHighlighter
from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
)

logger = logging.getLogger(__name__)


class VoicechatWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

    # Public:

    # Protected:
    _additional_client_to_elevenlabs_filters = [
        lambda message: message.get("type") == "client_tool_result"
    ]

    @client_tool_call(
        tool_name="go_to_section",
        required_parameters=["section", "question", "response", "language"],
    )
    async def _handle_go_to_section_tool(self, message: dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            logger.info(f"Go to section tool called with parameters: {parameters}")
            section_name = parameters.get("section")
            question = parameters.get("question")
            response = parameters.get("response")
            text_to_highlight = self.__compute_text_to_highlight(
                section_name, question, response
            )
            tool_call_uuid = tool_call.get("client_tool_call", {}).get(
                "tool_call_id", ""
            ).split("_")[-1] or uuid5(NAMESPACE_URL, "highlight_text")
            await self.send_message_to_client(
                {
                    "type": "client_tool_call",
                    "client_tool_call": {
                        "tool_name": "highlight_text",
                        "tool_call_id": f"highlight_text_{tool_call_uuid}",
                        "parameters": {
                            "section": section_name,
                            "text": text_to_highlight,
                        },
                    },
                }
            )
        except Exception as e:
            logger.error(f"Error handling go to section tool: {e}")

    # Private:
    def __compute_text_to_highlight(
        self, section_name: str, question: str, response: str
    ) -> str:
        return TextHighlighter().compute_text_to_highlight(
            section_name, question, response
        )
