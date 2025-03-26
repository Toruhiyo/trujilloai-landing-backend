import json
from difflib import SequenceMatcher
from typing import Any, Sequence


def flatten_list(ls: list[list[Any]]) -> list[Any]:
    return [item for sublist in ls for item in sublist]


def intersect_lists(ls1: list, ls2: list) -> list:
    if len(ls1) == 0:
        return ls2
    elif len(ls2) == 0:
        return ls1
    try:
        return list(set(ls1) & set(ls2))
    except Exception as e:
        msg = str(e)
        if (
            "unhashable type" in msg.lower()
            and isinstance(ls1[0], dict)
            and isinstance(ls2[0], dict)
        ):
            ls1 = list(map(json.dumps, ls1))
            s1 = set(ls1)
            ls2 = list(map(json.dumps, ls2))
            s2 = set(ls2)
            s = s1 & s2
            ls = list(map(json.loads, s))
            return ls
        raise e


def diff_lists(ls1: list, ls2: list) -> list:
    common = intersect_lists(ls1, ls2)
    return list(filter(lambda e: e not in common, make_unique(ls1 + ls2)))


def get_element_index(ls: list, element) -> int:
    index = [i for i, e in enumerate(ls) if element == e][0]
    return index


def get_element_indices(ls: list, element) -> list:
    return [i for i, e in enumerate(ls) if e == element]


def get_elements_by_indices(ls: list, indices) -> list:
    elements = []
    [elements.append(ls[i]) for i in indices]
    return elements


def get_elements_except_indices(ls: list, indices) -> list:
    elements = []
    for i, element in enumerate(ls):
        if i not in indices:
            elements.append(element)
    return elements


def get_element_by_type(ls: list, _type, index=0) -> list | None:
    matches = get_elements_by_type(ls, _type)
    if len(matches) > index or index == -1:
        return matches[index]
    else:
        return None


def get_elements_by_type(ls: list, _type) -> list:
    return list(filter(lambda e: isinstance(e, _type), ls))


def is_list_of_type(ls: list, _type) -> bool:
    if not isinstance(ls, list):
        raise TypeError("ls must be a list")
    if len(ls) == 0:
        raise ValueError("The list is empty")
    return all(list(map(lambda t: isinstance(t, _type), ls)))


def are_all_same_type(ls: list) -> bool:
    if not isinstance(ls, list) or len(ls) == 0:
        raise ValueError(f"Invalid type or empty list: {ls}.")
    types = get_list_element_types(ls)
    return is_list_of_type(ls, types[0])


def get_elements_type(ls: list) -> type:
    if not isinstance(ls, list) or len(ls) == 0:
        raise ValueError(f"Invalid type or empty list: {ls}.")
    if not are_all_same_type(ls):
        raise ValueError(f"All elements must be the same type. {ls}")
    return type(ls[0])


def get_list_element_types(ls: list) -> list:
    return list(map(type, ls))


def is_value_of_any_listed_type(value, types: Sequence) -> bool:
    return any(list(map(lambda t: isinstance(value, t), types)))


def remove_nones(ls: list) -> list:
    return list(filter(lambda e: e is not None, ls))


def remove_empty(ls: list) -> list:
    ls = remove_nones(ls)
    return list(
        filter(
            lambda e: (
                len(e) > 0
                if (
                    isinstance(e, str)
                    or isinstance(e, list)
                    or isinstance(e, dict)
                    or isinstance(e, tuple)
                    or isinstance(e, set)
                )
                else True
            ),
            ls,
        )
    )


def make_unique(ls) -> list[Any]:
    if len(ls) > 0:
        try:
            ls = list(set(ls))
        except Exception as e:
            msg = str(e)
            if "unhashable type" in msg.lower() and isinstance(ls[0], dict):
                ls = list(map(json.dumps, ls))
                ls = list(set(ls))
                ls = list(map(json.loads, ls))
                # ls = [dict(s) for s in set(frozenset(d.items()) for d in ls)]
            else:
                raise e
    return ls


def sort_list(ls) -> list[Any]:
    try:
        ls.sort()
    except Exception as e:
        msg = str(e)
        if "not supported between instances of " in msg.lower():
            pass
        else:
            raise e
    return ls


def get_most_repeated_element(ls: list) -> list[Any]:
    unique_elements = list(set(ls))
    repetions = list(map(lambda e: (e, ls.count(e)), unique_elements))
    _, counts = list(zip(*repetions))
    n = max(counts)
    t = list(filter(lambda t: t[1] == n, repetions))[0]
    return t[0]


def sort_strings_by_similarity(ls: list, s: str) -> list:
    def compute_similarity(ref) -> list:
        return SequenceMatcher(None, s, ref).ratio()

    sorted_values = sorted(ls, key=compute_similarity, reverse=True)
    return sorted_values


def find_most_similar_string(ls: list, s: str) -> str:
    if s in ls:
        match = s
    else:
        sorted_values = sort_strings_by_similarity(ls, s)
        match = sorted_values[0]
    return match


def get_string_in_list_by_substring(ls: list, substring: str) -> list:
    raise NotImplementedError


def transform_list(ls: list, f) -> list:
    return list(map(f, ls))


def filter_list(ls: list, f) -> list:
    return list(filter(f, ls))


def get_first_element(ls: list) -> list | None:
    return ls[0] if len(ls) > 0 else None


def get_first_match(f, ls) -> list | None:
    matches = list(filter(f, ls))
    return matches[0] if len(matches) > 0 else None


def get_list_missing_elements(ls: list, reference: Any) -> list[Any]:
    return [e for e in reference if e not in ls]


def find_duplicates_indices(ls) -> list[int]:
    indices = []
    counted_elements = []
    for i, e in enumerate(ls):
        if e not in counted_elements:
            idxs = get_element_indices(ls, e)
            counted_elements.append(e)
            if len(idxs) > 1:
                indices.append(idxs)
    return indices


def find_uniques_indices(ls) -> list[int]:
    return [i for i, e in enumerate(ls) if len(get_element_indices(ls, e)) == 1]


def unpack_list_of_lists(ls) -> list[int]:
    new_ls = []
    list(
        map(lambda e: new_ls.extend(e) if isinstance(e, list) else new_ls.append(e), ls)
    )
    return new_ls


def create_list_from_elements_count(elements_count) -> list:
    ls = []
    for element, n in elements_count:
        ls += create_list_of_duplicated_elements(element, n)
    return ls


def create_list_of_duplicated_elements(element: Any, n: int) -> list[Any]:
    ls = []
    for i in range(0, n):
        ls.append(element)
    return ls


def find_sequence_in_list(ls: list, sequence: list) -> list[tuple[int, int]]:
    indices = []
    for i, e in enumerate(ls):
        if e == sequence[0]:
            indices.append((i, i + len(sequence)))
            for j, e2 in enumerate(sequence):
                if i + j < len(ls) and ls[i + j] != e2:
                    indices.pop()
                    break
    return indices
