from pathlib import Path

from src.app.landing.enums import LanguageCode, SectionName
from src.app.voicechat.highlighting.dtos import HighlightedTextDTO
from src.app.voicechat.highlighting.llm_text_highlighting.llm_text_highlighter import (
    LlmTextHighlighter,
)
from src.config.vars_grabber import VariablesGrabber
from src.utils.metaclasses import DynamicSingleton
from src.utils.string_toolbox import convert_snake_to_kebab_case

DEFAULT_BEDROCK_MODEL_ID = (
    VariablesGrabber().get("AWS_BEDROCK_MODEL_ID")
    or "us.meta.llama3-2-1b-instruct-v1:0"
)

DEFAULT_SECTIONS_CONTENT_DIRECTORY = Path("src/app/landing/content")


class TextHighlighter(metaclass=DynamicSingleton):
    @property
    def model_id(self):
        return self.__llm_text_highlighter.model_id

    # Public:
    def __init__(
        self,
        model_id: str = DEFAULT_BEDROCK_MODEL_ID,
        sections_content_directory: Path = DEFAULT_SECTIONS_CONTENT_DIRECTORY,
    ):
        self.__llm_text_highlighter = LlmTextHighlighter(model_id=model_id)
        self.__load_section_paths(sections_content_directory)

    def compute(
        self,
        section_name: SectionName,
        question: str,
        response: str,
        language: LanguageCode,
    ) -> HighlightedTextDTO:
        section_content = self.__get_section_content(section_name, language)
        highlighted_text = self.__compute_text_to_highlight(
            question, response, section_content
        )
        highlighted_text.section = section_name
        highlighted_text.language = language
        return highlighted_text

    # Private:
    def __load_section_paths(self, sections_content_directory: Path):
        def get_section_filename(
            section_name: SectionName, language: LanguageCode
        ) -> str:
            return f"{language.value.lower()}-{convert_snake_to_kebab_case(section_name.value).lower()}.txt"

        self.__section_paths = {
            language: {
                section_name: sections_content_directory
                / language.value.lower()
                / get_section_filename(section_name, language)
                for section_name in SectionName
            }
            for language in LanguageCode
        }

    def __get_section_content(
        self, section_name: SectionName, language: LanguageCode
    ) -> str:
        return self.__section_paths[language][section_name].read_text()

    def __compute_text_to_highlight(
        self,
        question: str,
        response: str,
        section_content: str,
    ) -> HighlightedTextDTO:

        return self.__llm_text_highlighter.compute(question, response, section_content)
