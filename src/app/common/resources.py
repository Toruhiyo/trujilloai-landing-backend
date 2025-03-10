from typing import Optional
from src.app.errors import BadRequestError, ForbiddenRequestError


def validate_params(
    params: dict, valid_fields: list[str], forbidden_params: Optional[list[str]] = None
) -> dict:
    forbidden_params = forbidden_params or []
    if any([key not in valid_fields for key in params.keys()]):
        raise BadRequestError(f"Invalid params: {params}")
    forbidden_params = list(filter(lambda k: k in forbidden_params, params.keys()))
    if len(forbidden_params) > 0:
        raise ForbiddenRequestError(f"Forbidden params: {forbidden_params}")
    return params
