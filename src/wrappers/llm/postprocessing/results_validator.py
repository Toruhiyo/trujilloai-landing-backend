import json
from datetime import datetime
from pathlib import Path

from data_structures_utils.dict_toolbox import CaseType, convert_keys_case
from jsonschema import SchemaError, ValidationError, validate


class ResultsValidator:

    # Public:
    def __init__(
        self, schema: dict | Path | None, __date_format: str = "%Y-%m-%d"
    ) -> None:
        self.__schema = (
            json.loads(schema.read_text()) if isinstance(schema, Path) else schema
        )
        self.__date_format = __date_format

    def validate(self, results: dict | Exception | None) -> dict | Exception | None:
        self._results = results
        if isinstance(self._results, dict):
            # if len(self._results) == 0:
            #     return None
            if self.__schema is not None:
                self.__ensure_schema()
            self.__format_data()
        return self._results

    # Private:
    def __ensure_schema(self) -> None:
        schema = self.__schema
        if schema is None:
            raise ValueError(f"Invalid schema type: {schema}.")
        if isinstance(self._results, dict):
            try:
                validate(instance=self._results, schema=schema)
            except (SchemaError, ValidationError) as e:
                self._results = e

    def __format_data(self) -> None:
        results = self._results
        if isinstance(results, dict):
            results = convert_keys_case(results, CaseType.KEBAB, recursive=True)
            # !! MAKE GENERAL !!
            if "date" in results:
                results["date"] = self.__format_date(results.get("date"))
            self._results = results

    def __format_date(self, date) -> datetime | Exception | None:
        if date is None:
            return
        if isinstance(date, str):
            date = datetime.strptime(date, self.__date_format)
        else:
            date = TypeError(f'Invalid date type "{type(date)}". Must be a string.')
        return date
