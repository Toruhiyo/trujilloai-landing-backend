import json
import re
from src.app.demos.ai_bi.nlq.enums import Unit
from pathlib import Path

DEFAULT_UNITS_DICTIONARY_PATH = Path(__file__).parent / "columns-units-dictionary.json"


class ColumnUnitsAssigner:
    def __init__(self, units_dictionary_path: Path = DEFAULT_UNITS_DICTIONARY_PATH):
        self.__units_dictionary_path = units_dictionary_path
        self.__units_dictionary = self.__load_units_dictionary()
        self.__compiled_patterns = self.__compile_patterns()

    def compute(self, columns: list[str]) -> list[Unit | None]:
        return [self.__get_column_unit(column) for column in columns]

    # Private:
    def __load_units_dictionary(self) -> dict[str, list[str]]:
        return json.loads(self.__units_dictionary_path.read_text())

    def __compile_patterns(self) -> dict[str, list[re.Pattern]]:
        compiled_patterns = {}
        for unit, patterns in self.__units_dictionary.items():
            compiled_patterns[unit] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        return compiled_patterns

    def __get_column_unit(self, column: str) -> Unit | None:
        for unit, patterns in self.__compiled_patterns.items():
            if any(pattern.search(column) for pattern in patterns):
                return Unit(unit)
        return None
