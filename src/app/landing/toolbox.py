from src.app.landing.enums import LanguageCode, SectionName


def typify_language(language: str) -> LanguageCode:
    return LanguageCode(language.lower())


def typify_section_name(section_name: str) -> SectionName:
    return SectionName(section_name.upper())
