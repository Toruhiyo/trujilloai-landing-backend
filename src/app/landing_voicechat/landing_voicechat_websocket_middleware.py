import json
import logging
import re
from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from src.app.landing.enums import LanguageCode, SectionName
from src.app.landing.toolbox import typify_language, typify_section_name
from src.app.landing_voicechat.email_formatting.email_formatter import EmailFormatter
from src.app.landing_voicechat.animations_triggering.enums import (
    AnimationName,
    AnimationLifecycle,
)
from src.app.landing_voicechat.highlighting.dtos import HighlightedTextDTO
from src.app.landing_voicechat.highlighting.text_highlighter import TextHighlighter
from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
    client_tool_call,
    agent_response_event,
)

logger = logging.getLogger(__name__)

DEFAULT_ANIMATION_TRIGGERS_FILE_PATH = (
    Path(__file__).parent / "animations_triggering" / "triggers.json"
)


class LandingVoicechatWebsocketMiddleware(ElevenLabsWebsocketMiddleware):

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

    def __init__(
        self,
        *args,
        animation_triggers_file_path: Path = DEFAULT_ANIMATION_TRIGGERS_FILE_PATH,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._animation_triggers = json.loads(
            animation_triggers_file_path.read_text(encoding="utf-8")
        )

    @client_tool_call(
        tool_name="fill_contact_form",
        required_parameters=[],
        await_handler=True,
    )
    async def _handle_fill_contact_form_tool(self, message: dict[str, Any]):
        try:
            tool_call = message.get("client_tool_call", {})
            parameters = tool_call.get("parameters", {})
            logger.info(f"Fill contact form tool called with parameters: {parameters}")
            email = parameters.get("email")
            if email:
                formatted_email = self.__ensure_email_format(email)
                if formatted_email != email:
                    parameters["email"] = formatted_email
                    logger.info(f"Email formatted: {formatted_email}")
            message["parameters"] = parameters
            return message
        except Exception as e:
            logger.error(f"Error handling fill contact form tool: {e}")

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
            await self.send_client_tool_call(
                tool_name="highlight_text",
                tool_call_id=f"highlight_text_{tool_call_uuid}",
                parameters={
                    "section": section_name.value,
                    "texts": highlighted_text_results.texts,
                },
            )
        except Exception as e:
            logger.error(f"Error handling go to section tool: {e}")

    @agent_response_event(await_handler=False)
    async def _handle_animation_triggering_from_transcript(
        self, message: dict[str, Any]
    ):
        try:
            agent_response_data = message.get("agent_response_event", {})
            agent_response = agent_response_data.get("agent_response", "")

            if not agent_response:
                return

            animation_name, lifecycle = self.__detect_animation_trigger(agent_response)
            if animation_name:
                tool_call_uuid = str(
                    uuid5(NAMESPACE_URL, f"animation_{animation_name.value}")
                )
                await self.send_client_tool_call(
                    tool_name="trigger_animation",
                    tool_call_id=f"trigger_animation_{tool_call_uuid}",
                    parameters={
                        "name": animation_name.value,
                        "lifecycle": lifecycle.value if lifecycle else "once",
                    },
                )
                logger.info(
                    f"Triggered {animation_name.value} animation with lifecycle: "
                    f"{lifecycle.value if lifecycle else 'once'}"
                )
        except Exception as e:
            logger.error(f"Error handling agent response animation: {e}")

    # Private:
    def __ensure_email_format(self, email: str) -> str:
        return EmailFormatter().compute(email)

    def __compute_text_to_highlight(
        self,
        section_name: SectionName,
        question: str,
        response: str,
        language: LanguageCode,
    ) -> HighlightedTextDTO:
        return TextHighlighter().compute(section_name, question, response, language)

    def __detect_animation_trigger(
        self, agent_response: str
    ) -> tuple[AnimationName | None, AnimationLifecycle | None]:
        for trigger_config in self._animation_triggers:
            patterns_by_language = trigger_config["patterns"]
            all_patterns = []

            # Combine patterns from all languages
            for language_patterns in patterns_by_language.values():
                all_patterns.extend(language_patterns)

            pattern_string = r"\b(?:" + "|".join(all_patterns) + r")\b"
            compiled_pattern = re.compile(pattern_string, re.IGNORECASE)

            if compiled_pattern.search(agent_response):
                logger.info(f"Detected animation trigger: {trigger_config.get('name')}")
                animation_name = trigger_config.get("animation")
                lifecycle = trigger_config.get("lifecycle") or "once"

                return (
                    AnimationName(animation_name) if animation_name else None,
                    AnimationLifecycle(lifecycle),
                )

        return None, None
