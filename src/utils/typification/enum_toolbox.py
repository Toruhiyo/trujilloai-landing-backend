from enum import Enum, EnumMeta
from typing import Any


def value2enum(value: Any, enum: EnumMeta) -> Enum:
    matches = list(
        filter(lambda e: e.value == value if isinstance(e, Enum) else False, enum)
    )
    if len(matches) == 0:
        raise Exception(f"Did not find any match for {value} in {enum}.")
    match = matches[0]
    if not isinstance(match, Enum):
        raise ValueError(f"Found a match for {value} in {enum}, but it is not an Enum.")
    return match
