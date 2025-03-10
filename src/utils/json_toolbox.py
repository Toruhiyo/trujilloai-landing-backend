from decimal import Decimal
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def load_json(filepath: Path | str, encoding: str = "ascii") -> dict | list:
    with open(filepath, encoding=encoding) as f:
        data = json.load(f)
    return data


def load_if_json(filepath: Path | str, encoding: str = "ascii") -> dict | list | Any:
    if isinstance(filepath, str) or isinstance(filepath, Path):
        if Path(filepath).suffix == ".json":
            data = load_json(filepath, encoding=encoding)
            return data
    return filepath


def export_json(filepath: Path | str, data: dict | list) -> None:
    with open(filepath, "w") as f:
        string = json.dumps(data, indent=4)
        f.write(string)


def load_jsons_in_directory(
    directory: Path, encoding: str = "ascii"
) -> list[dict | list]:
    return [
        load_json(file, encoding=encoding)
        for file in directory.iterdir()
        if file.suffix == ".json"
    ]


def make_serializable(value: Any, date_format: str | None = None, **kwargs) -> Any:
    if isinstance(value, dict):
        value = {
            make_serializable(k, date_format=date_format, **kwargs): make_serializable(
                v, date_format=date_format, **kwargs
            )
            for k, v in value.items()
        }
    elif isinstance(value, (list, tuple)):
        value = [make_serializable(v, date_format=date_format, **kwargs) for v in value]
    elif isinstance(value, datetime) or isinstance(value, date):
        if date_format:
            value = value.strftime(date_format)
        else:
            value = value.isoformat()
    elif isinstance(value, set):
        value = make_serializable(list(value), date_format=date_format, **kwargs)
    elif isinstance(value, BaseModel):
        value = make_serializable(value.dict(), date_format=date_format, **kwargs)
    elif isinstance(value, Enum):
        value = make_serializable(value.value, date_format=date_format, **kwargs)
    elif isinstance(value, Path):
        value = str(value)
    elif isinstance(value, Exception):
        value = f"{type(value)}-{value}"
    elif isinstance(value, Decimal):
        value = str(value)
    elif isinstance(value, bytes):
        value = value.decode()
    elif isinstance(value, complex):
        value = str(value)
    elif isinstance(value, DataFrame):
        value = value.to_csv(index=False)
    elif isinstance(value, object):
        if hasattr(value, "__dict__"):
            value = make_serializable(value.__dict__, date_format=date_format, **kwargs)
    else:
        pass
    return json.loads(json.dumps(value, **kwargs))


def is_jsonable(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except Exception:
        return False
