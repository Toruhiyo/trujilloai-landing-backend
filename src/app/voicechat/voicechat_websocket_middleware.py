import logging
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from src.app.landing.enums import LanguageCode, SectionName
from src.app.landing.toolbox import typify_language, typify_section_name
from src.app.voicechat.highlighting.dtos import HighlightedTextDTO
from src.app.voicechat.highlighting.text_highlighter import TextHighlighter
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

    _highlightable_sections = [
        SectionName.HERO,
        SectionName.SERVICES,
        SectionName.WHY_CHOOSE_ORIOL,
        SectionName.HOW_SOLO_OR_SQUAD,
        SectionName.HOW_METHODOLOGY,
        SectionName.SELECTED_PROJECTS,
        SectionName.BIO,
    ]

    @client_tool_call(
        tool_name="go_to_section",
        required_parameters=["section", "question", "response", "language"],
        await_handler=False,
    )
    async def _handle_go_to_section_tool(self, message: dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            logger.info(f"Go to section tool called with parameters: {parameters}")
            section_name = typify_section_name(parameters["section"])
            question = parameters["question"]
            response = parameters["response"]
            language = typify_language(parameters["language"])

            if section_name not in self._highlightable_sections:
                logger.info(
                    f"Section {section_name} is not highlightable, skipping highlighting"
                )
                return

            highlighted_text_results = self.__compute_text_to_highlight(
                section_name, question, response, language
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
                            "section": section_name.value,
                            "texts": highlighted_text_results.texts,
                        },
                    },
                }
            )
        except Exception as e:
            logger.error(f"Error handling go to section tool: {e}")

    # Private:
    def __compute_text_to_highlight(
        self,
        section_name: SectionName,
        question: str,
        response: str,
        language: LanguageCode,
    ) -> HighlightedTextDTO:
        return TextHighlighter().compute(section_name, question, response, language)
