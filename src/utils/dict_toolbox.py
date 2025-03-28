from datetime import date, datetime
from enum import Enum
from typing import Any, Sequence

from .list_toolbox import is_value_of_any_listed_type, make_unique, sort_list
from .string_toolbox import CaseType, convert_string_case


class NumericMergeType(Enum):
    SUM = "sum"
    OVERWRITE = "overwrite"
    KEEP = "keep"
    MAX = "max"
    MIN = "min"


def check_keys(d: dict, keys: list or tuple):
    missing_keys = get_missing_keys(d, keys)
    if len(missing_keys) > 0:
        raise KeyError(
            f"Dictionary has not all requestes keys. Missing: {missing_keys}"
        )


def has_all_keys(d: dict, keys: list or tuple):
    return len(get_missing_keys(d, keys)) == 0


def get_missing_keys(d, keys):
    return list(k for k in keys if k not in d)


def rename_keys(d, keys_dict, ignore_missing_keys=False):
    for old_key, new_key in keys_dict.items():
        if old_key in d:
            d[new_key] = d.pop(old_key)
        elif not ignore_missing_keys:
            raise KeyError(f"Old key <{old_key}> not found in input dictionary.")
    return d


def convert_keys_case(d: dict, case: CaseType, recursive: bool = False) -> dict:
    if recursive:
        return {
            convert_string_case(k, case): (
                convert_keys_case(v, case, recursive=recursive)
                if isinstance(v, dict)
                else v
            )
            for k, v in d.items()
        }
    return {convert_string_case(k, case): v for k, v in d.items()}


def get_list_of_values_from_dict_per_depth_level(d: dict, depth: int) -> list[Any]:
    values = []
    for key, value in d.items():
        if type(value) is dict:
            if depth - 1 == 1:
                values.extend(list(value.values()))
            elif depth > 0:
                values.extend(
                    get_list_of_values_from_dict_per_depth_level(value, depth - 1)
                )
            else:
                raise Exception("Invalid depth level. Must be >= 0.")
        else:
            values.append({key: value})
    return values


def get_values_from_dict_by_depth_level(d: dict, depth_level: int) -> dict | list[Any]:
    if depth_level == 0:
        return d
    else:
        values = []
        for key, value in d.items():
            if type(value) is dict:
                values.extend(
                    get_values_from_dict_by_depth_level(value, depth_level - 1)
                )
            else:
                values.append(value)
        return values


def multilevel_dictionary_search(d: dict, path: str, ignore_case=False):
    try:
        keys = path.split("/")
        for key in keys:
            if ignore_case:
                d = get_value_ignoring_case(d, key)
            else:
                d = d[key]
        return d
    except KeyError as exception:
        msg = str(exception)
        raise Exception(
            f"Invalid path ({path}) for this dictionary. {key} key not found."
        )
    except Exception as exception:
        raise exception


def get_value_ignoring_case(d: dict, key: str):
    if type(key) is not str:
        raise TypeError("Invalid type for specified key <{key}>. Must be a string.")
    ls = list(
        filter(lambda k: k.lower() == key.lower() if type(k) is str else False, d)
    )
    if len(ls) > 0:
        return d[ls[0]]
    else:
        return KeyError(f"Key <{key}> not fount in dictionary.")


def remove_keys_from_dict(
    d: dict, keys: list[str], ignore_missing_keys: bool = False
) -> dict:
    if ignore_missing_keys:
        valid_keys = d.keys()
        keys = list(filter(lambda key: key in valid_keys, keys))
    else:
        check_keys(d, keys)
    return {k: v for k, v in d.items() if k not in keys}


def remove_other_keys_from_dict(d: dict, keys: list[str]) -> dict:
    return {k: v for k, v in d.items() if k in keys}


def get_key_value_pairs_by_keys(d: dict, keys: Sequence[Any]) -> dict:
    return remove_other_keys_from_dict(d, keys)


def get_unique_keys_from_list_of_dicts(d):
    keys = []

    def f(row):
        return keys.extend(list(row.keys()))

    list(map(f, d))
    keys = list(set(keys))
    return keys


def get_unique_values_for_key_from_list_of_dicts(ls, key):
    values = get_values_from_list_of_dicts_by_key(ls, key)
    values = list(set(values))
    return values


def update_dictionary(d, changes) -> dict:
    for key, value in changes.items():
        if key in d:
            if type(value) is dict:
                value = update_dictionary(d[key], value)
            else:
                d[key] = value
        else:
            raise Exception(f"Not found field <{key}>")
    return d


def merge_dicts(d1: dict, d2: dict, **kwargs) -> dict:
    for key, value in d2.items():
        if key not in d1:
            d1[key] = value
        else:
            try:
                d1[key] = merge_values(
                    d1[key],
                    value,
                    **kwargs,
                )
            except Exception as e:
                raise Exception(f"Error merging key <{key}>. Message: <{str(e)}>.")
    return d1


def merge_values(
    v1: Any,
    v2: Any,
    ignore_errors: bool = False,
    numeric_merge_type: NumericMergeType = NumericMergeType.SUM,
    lists_unique: bool = False,
    lists_sort: bool = False,
    exclude_types: Sequence = [],
    extra_types_assignation: list | None = None,
    extra_types_sum: list | None = None,
):
    extra_types_assignation = extra_types_assignation or []
    extra_types_sum = extra_types_sum or []
    value = v1
    if is_value_of_any_listed_type(v2, exclude_types):
        return value
    if isinstance(v2, type(value)):
        if isinstance(v2, list):
            value += v2
            if lists_unique:
                value = make_unique(value)
            if lists_sort:
                value = sort_list(value)
        elif isinstance(v2, int) or isinstance(v2, float):
            match numeric_merge_type:
                case NumericMergeType.SUM:
                    value += v2
                case NumericMergeType.OVERWRITE:
                    value = v2
                case NumericMergeType.KEEP:
                    pass
                case NumericMergeType.MAX:
                    value = max(value, v2)
                case NumericMergeType.MIN:
                    value = min(value, v2)
                case _:
                    raise NotImplementedError(
                        "Invalid v2 for <numeric_merge_type> variable. Valid v2s are <sum>, <overwrite> or <keep>."
                    )
        elif isinstance(v2, dict):
            value = merge_dicts(
                value,
                v2,
                numeric_merge_type=numeric_merge_type,
                lists_unique=lists_unique,
                lists_sort=lists_sort,
            )
        elif isinstance(v2, str):
            value = v2
        elif isinstance(v2, datetime) or isinstance(v2, date):
            value = v2
        elif v2 is None:
            pass
        elif type(v2) in extra_types_assignation:
            value = v2
        elif type(v2) in extra_types_sum:
            value += v2
        else:
            raise NotImplementedError(f"Still not defined for {type(v2)} type.")
    elif v2 is None:
        pass
    elif v2 is not None:
        value = v2
    elif ignore_errors:
        value = v2
    else:
        raise TypeError(f"Type mismatch: <{type(v2)} != {type(value)}>")
    return value


def merge_elements_in_list(
    ls: list[Any],
    **kwargs,
):
    accum = None
    for e in ls:
        accum = merge_values(accum, e, **kwargs)
    return accum


def merge_dicts_in_list(
    dicts_list: list[dict],
    ignore_errors: bool = False,
    numeric_merge_type=NumericMergeType.SUM,
    lists_unique: bool = False,
    lists_sort: bool = False,
) -> dict:
    accum_dict = {}
    for d in dicts_list:
        accum_dict = merge_dicts(
            accum_dict,
            d,
            ignore_errors=ignore_errors,
            numeric_merge_type=numeric_merge_type,
            lists_unique=lists_unique,
            lists_sort=lists_sort,
        )
    return accum_dict


def merge_all_dicts_in_dict(
    d,
    ignore_errors=False,
    numeric_merge_type="sum",
    lists_unique=False,
    lists_sort=False,
):
    return merge_all_values_of_specific_type_in_dict(
        d,
        dict,
        ignore_errors=ignore_errors,
        numeric_merge_type=numeric_merge_type,
        lists_unique=lists_unique,
        lists_sort=lists_sort,
    )


def merge_all_values_of_specific_type_in_dict(
    d,
    _type,
    ignore_errors=False,
    numeric_merge_type="sum",
    lists_unique=False,
    lists_sort=False,
):
    if _type is dict:
        merged = {}
    elif _type is list:
        merged = []
    else:
        NotImplementedError(f"Not implemented merge for type <{_type}>.")
    for value in d.values():
        if type(value) is _type:
            if _type is dict:
                merged = merge_dicts(
                    merged,
                    value,
                    ignore_errors=ignore_errors,
                    numeric_merge_type=numeric_merge_type,
                    lists_unique=lists_unique,
                    lists_sort=lists_sort,
                )
            elif _type is list:
                merged += value
                if lists_unique:
                    merged = make_unique(merged)
                if lists_sort:
                    merged = sort_list(merged)
    return merged


def get_all_values_of_specific_types(d, types):
    if type(types) is not list:
        raise TypeError(f"Argument <types> must be a <list> not <{type(types)}>-type.")
    return list(filter(lambda v: type(v) in types, d.values()))


def get_dict_from_list_by_key_value(ls, key, value):
    matches = get_dicts_from_list_by_key_value(ls, key, value)
    if len(matches) > 0:
        match = matches[0]
    else:
        match = None
    return match


def get_values_from_dict_by_keys(d, keys, ignore_missing_keys=False, merge_lists=False):
    if ignore_missing_keys:
        valid_keys = d.keys()
        keys = list(filter(lambda key: key in valid_keys, keys))
    else:
        check_keys(d, keys)
    return list(map(lambda key: d[key], keys))


def compare_dicts_by_keys(d1, d2, keys=None, ignore_missing_keys=False):
    if type(d1) is not dict or type(d2) is not dict:
        raise TypeError(
            f"Both input arguments d1 and d2 must be of type <dict> not <{type(d1)}> and <{type(d2)}>."
        )
    if keys is None:
        keys = make_unique(list(d1.keys()) + list(d2.keys()))
    for key in keys:
        try:
            if d1[key] != d2[key]:
                return False
        except KeyError as e:
            if ignore_missing_keys:
                pass
            else:
                raise e
    return True


def get_dicts_from_list_by_key_type(ls: list[dict], key: Any, _type: Any) -> list[dict]:
    return get_dicts_from_list_by_key_types(ls, key, [_type])


def get_dicts_from_list_by_key_types(
    ls: list[dict], key: Any, types: Sequence[Any]
) -> list[dict]:
    return list(
        filter(lambda d: any([isinstance(d[key], _type) for _type in types]), ls)
    )


def get_dicts_from_list_by_key_value(ls, key, value):
    return get_dicts_from_list_by_key_values(ls, key, [value])


def get_dicts_from_list_by_key_values(ls, key, values):
    return list(filter(lambda d: d[key] in values, ls))


def get_values_from_list_of_dicts_by_key(ls, key):
    return list(map(lambda d: d[key], ls))


def get_values_from_list_of_dicts_by_keys(ls, keys):
    def func(d):
        return [d[k] for k in keys]

    return list(map(func, ls))


def get_keys_from_dict_of_type(d, _type):
    keys = list(d.keys())
    return list(filter(lambda key: type(d[key]) is _type, keys))


def get_values_from_dict_of_type(d, _type):
    values = list(d.values())
    return list(filter(lambda value: type(value) is _type, values))


def remove_keys_from_dict_of_type(d, _type):
    type_keys = get_keys_from_dict_of_type(d, _type)
    d = remove_keys_from_dict(d, type_keys)
    return d


def get_values_from_dict_by_subkey(d, subkey):
    return list(map(lambda value: value[subkey], d.values()))


def get_values_from_dict_by_subkeys(d, subkeys):
    return list(map(lambda value: [value[subkey] for subkey in subkeys], d.values()))


def get_values_from_dict_by_subkey_value(d, subkey, value):
    return list(filter(lambda v: v[subkey] == value, d.values()))


def remove_subkeys_from_dicts(d, subkeys):
    return {k: remove_keys_from_dict(v, subkeys) for k, v in d.items()}


def remove_other_subkeys_from_dicts(d, subkeys):
    return {k: remove_other_keys_from_dict(v, subkeys) for k, v in d.items()}


def remove_keys_from_dict_list(
    ls: list[dict], keys: list[str], ignore_missing_keys: bool = False
) -> list[dict]:
    return [
        remove_keys_from_dict(d, keys, ignore_missing_keys=ignore_missing_keys)
        for d in ls
    ]


def remove_other_keys_from_dict_list(ls, keys):
    return [remove_other_keys_from_dict(d, keys) for d in ls]


def remove_dicts_matching_key_values_from_dict_list(
    ls, key, values, transformation=None
):
    if transformation is None:
        return list(filter(lambda d: d[key] not in values, ls))
    else:
        values = [transformation(v) for v in values]
        return list(filter(lambda d: transformation(d[key]) not in values, ls))


def remove_dicts_not_matching_key_values_from_dict_list(
    ls, key, values, transformation=None
):
    values = list(set(values))
    if transformation is None:

        def f(d):
            try:
                return d[key] in values
            except Exception:
                return False

    else:
        values = [transformation(v) for v in values]

        def f(d):
            try:
                return transformation(d[key]) in values
            except Exception:
                return False

    return list(filter(lambda d: f(d), ls))


def get_merged_values_from_dict_by_subkey(
    d,
    subkey,
    ignore_errors=False,
    numeric_merge_type="sum",
    lists_unique=False,
    lists_sort=False,
):
    return merge_dicts_in_list(
        get_values_from_dict_by_subkey(d, subkey),
        ignore_errors=ignore_errors,
        numeric_merge_type=numeric_merge_type,
        lists_unique=lists_unique,
        lists_sort=lists_sort,
    )


def get_merged_list_values(d):
    ls = []
    list(ls.extend(l) for l in d.values() if type(l) is list)
    return ls


def sort_by_subkey_value(d, subkey, reverse=True):
    return sorted(d, key=lambda key: d[key][subkey], reverse=reverse)


def sort_list_of_dicts_by_subkey_value(
    ls: list[dict], subkey: Any, reverse: bool = False
) -> list[dict]:
    return sorted(ls, key=lambda d: d[subkey], reverse=reverse)


def get_most_relevant_entry_by_subkey_value(d, subkey, reverse=True):
    sorted_entries = sort_by_subkey_value(d, subkey, reverse=reverse)
    if len(sorted_entries) > 0:
        return sorted_entries[0]
    else:
        return None


def set_values_from_list_to_dicts_by_key(dicts, key, values):
    for dict, value in zip(dicts, values):
        dict[key] = value
    return dicts


def transform_dictionary(d, f):
    return {k: f(v) for k, v in d.items()}


def filter_dictionary(d, f):
    return {k: v for k, v in d.items() if f(v)}


def transform_dictionary_value_by_key(d, k, f):
    d[k] = f(d[k])
    return d
