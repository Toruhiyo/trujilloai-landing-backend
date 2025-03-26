
import string
import unicodedata
from enum import Enum


class CaseType(Enum):
    SNAKE = "snake"
    KEBAB = "kebab"
    SCREAMING_KEBAB = "screaming_kebab"
    LOWER_CAMMEL = "lower_cammel_case"
    UPPER_CAMEL = "upper_camel_case"

    def __str__(self) -> str:
        return str(self.value)


def convert_string_case(s: str, case_type: CaseType) -> str:
    match case_type:
        case CaseType.SNAKE:
            return convert_to_snake_case(s)
        case CaseType.KEBAB:
            return convert_to_kebab_case(s)
        case CaseType.SCREAMING_KEBAB:
            return convert_to_screaming_kebab_case(s)
        case CaseType.LOWER_CAMMEL:
            raise NotImplementedError("Not implemented yet")
        case CaseType.UPPER_CAMEL:
            raise NotImplementedError("Not implemented yet")
        case _:
            raise ValueError(f"Unknown case type: {case_type}")


def get_number_from_string(s: str) -> int:
    try:
        return int("".join([c for c in s if c.isdigit()]))
    except Exception as e:
        raise Exception(f"Cannot get number from strin: {s}. Message: {e}")


def append_prefix_to_strings(ls, prefix):
    return [prefix + s for s in ls]


def remove_word(s, w):
    return s.replace(w, "", 1)


def remove_starting_whitespaces(s: str) -> str:
    while s.startswith(" "):
        s = s[1:]
    return s


def remove_whitespaces(s: str) -> str:
    return s.replace(" ", "")


def remove_double_whitespaces(s: str) -> str:
    return remove_double_substring(s, " ")


def remove_double_substring(s: str, c: str):
    double_c = "".join([c] * 2)
    while double_c in s:
        s = s.replace(double_c, c)
    return s


def remove_ending_whitespaces(s: str) -> str:
    while s.endswith(" "):
        s = s[:-1]
    return s


def normalize(s, form="NFKC"):
    return unicodedata.normalize(form, s)


def remove_punctuation(s: str) -> str:
    return s.translate(str.maketrans("", "", string.punctuation))


def get_first_word(s: str) -> str:
    if isinstance(s, str):
        words = s.split()
        if len(words) > 0:
            return words[0]
    return s


def get_last_word(s: str) -> str:
    if isinstance(s, str):
        words = s.split()
        if len(words) > 0:
            return words[-1]
    return s


def count_words(s: str) -> int:
    return len(s.split())

def convert_snake_to_kebab_case(string: str) -> str:
    return string.replace("_", "-")

def convert_to_snake_case(s: str) -> str:
    if len(s) > 1:
        s = s.replace(" ", "_").replace("-", "_")
        s = s[0].lower() + s[1:]
        s = "".join(
            [
                f"_{c.lower()}"
                if c.isupper() and i < len(s) and s[i + 1].islower()
                else c.lower()
                for i, c in enumerate(s)
            ]
        )
    else:
        s = s.lower()
    s = remove_double_substring(s, "_")
    return s


def convert_to_kebab_case(s: str) -> str:
    return s.lower().replace(" ", "-")


def convert_to_screaming_kebab_case(s: str) -> str:
    return s.upper().replace(" ", "-")


def copy_case(s, ref):
    if not isinstance(s, str) and type(ref) is not ref:
        raise TypeError("Both input arguments must be strings.")
    if len(s) > 0 and len(ref) > 0:
        if ref.isupper():
            return s.upper()
        elif ref.islower():
            return s.lower()
        elif ref[0].isupper():
            return s.capitalize()
    return s


def get_class_name(obj):
    name = str(obj.__class__)
    name = name.split("'>")[0]
    name = name.split(".")[-1]
    return name


def contains_any_substring(
    s: str, substrings: list[str], ignore_case: bool = False
) -> bool:
    if ignore_case:
        s = s.lower()
        substrings = [sub.lower() for sub in substrings]
    for substring in substrings:
        if substring in s:
            return True
    return False


def contains_all_substrings(
    s: str, substrings: list[str], ignore_case: bool = False
) -> bool:
    if ignore_case:
        s = s.lower()
        substrings = [sub.lower() for sub in substrings]
    for substring in substrings:
        if substring not in s:
            return False
    return True


def remove_brackets(s: str) -> str:
    return (
        s.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("{", "")
        .replace("}", "")
    )


def make_plural(word: str) -> str:
    if word.endswith("y"):
        return f"{word[:-1]}ies"
    elif word.endswith("s"):
        return word
    return f"{word}s"