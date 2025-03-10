import logging
from typing import Optional


from .dtos import (
    UserInputDTO,
    UserDTO,
)

from src.app.generic_dtos import KeyValuePairDTO
from src.wrappers.aws.errors import CognitoUserNotFoundError
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.aws.cognito import CognitoWrapper
from src.app.errors import BadRequestError, UserNotFoundError
from src.utils.json_toolbox import make_serializable

logger = logging.getLogger(__name__)

USER_POOL_ID = VariablesGrabber().get("AWS_COGNITO_USER_POOL_ID")
DEFAULT_QUERY_LIMIT = None


def list_users(
    limit: Optional[int] = DEFAULT_QUERY_LIMIT,
) -> list[UserDTO]:
    users = CognitoWrapper().list_users(USER_POOL_ID)
    users = list(
        map(
            lambda u: typify_user(u),
            users,
        )
    )
    users = sorted(users, key=lambda u: u["created_at"], reverse=True)
    if isinstance(limit, int):
        users = users[:limit]
    logger.debug(f"Retrieving users '{users}'")
    return [UserDTO(**user) for user in users]


def create_user(
    user_data: UserInputDTO,
) -> UserDTO:
    validate_input_user_data(user_data)
    logger.info(f"Creating user '{user_data.username}'")
    user_inserted = CognitoWrapper().create_user(
        USER_POOL_ID,
        user_data=make_serializable(user_data),
    )
    user_inserted = UserDTO(**user_inserted)
    logger.debug(f"User {user_inserted.username} has been created")
    return user_inserted


def validate_input_user_data(user_data: UserInputDTO):
    try:
        UserInputDTO(**user_data.dict())
    except Exception as e:
        raise BadRequestError(f"Invalid user data: {e}")


def get_user(username: str) -> UserDTO:
    logger.debug(f"Retrieving user '{username}'")
    try:
        user = CognitoWrapper().get_user(USER_POOL_ID, username)
        user = typify_user(user)
        return UserDTO(**user)
    except CognitoUserNotFoundError as e:
        logger.error(f"Error getting user: {e}")
        raise UserNotFoundError(f"Not found user '{username}'")


def delete_user(username: str) -> bool:
    logger.info(f"Deleting user '{username}'")
    try:
        return CognitoWrapper().delete_user(
            USER_POOL_ID,
            username,
            check_existence=True,
        )
    except CognitoUserNotFoundError as e:
        logger.error(f"Error deleting user: {e}")
        raise UserNotFoundError(f"User with id {username} not found")


def update_user(
    username: str,
    params: dict,
) -> UserDTO:
    key_user = {"key": username}
    logger.info(f"Updating user '{username}' ")
    get_user(username)
    (
        expression,
        attribute_names,
        attribute_values,
    ) = generate_update_expression(params)
    try:
        CognitoWrapper().update_user(
            USER_POOL_ID,
            key_user,
            expression,
            attribute_names,
            attribute_values,
        )
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise e

    return get_user(username)


def validate_user(username: str) -> None:
    if not is_user_valid(username):
        raise BadRequestError(f"Invalid username: {username}")


def is_user_valid(username: str) -> bool:
    if not isinstance(username, str):
        return False
    try:
        get_user(username)
        return True
    except BadRequestError:
        return False


def generate_update_expression(params: dict):
    expression_parts = []
    attribute_names = {}
    attribute_values = {}
    for key, value in params.items():
        if key not in KeyValuePairDTO.__fields__:
            raise ValueError(f"Invalid key: {key}")
        expression_parts.append(f"#{key} = :{key}")
        attribute_names[f"#{key}"] = key
        attribute_values[f":{key}"] = value
    expression = f"SET {', '.join(expression_parts)}"
    return expression, attribute_names, attribute_values


def typify_user(user: dict) -> dict:
    def get_user_attribute(user: dict, attribute: str, ignore_case: bool = True):
        attributes = user.get("Attributes") or user.get("UserAttributes") or []
        for attr in attributes:
            if ignore_case:
                if attr["Name"].lower() == attribute.lower():
                    return attr["Value"]
            else:
                if attr["Name"] == attribute:
                    return attr["Value"]
        return None

    return {
        "username": user["Username"],
        "email": get_user_attribute(user, "email"),
        "created_at": user["UserCreateDate"],
        "updated_at": user["UserLastModifiedDate"],
        "enabled": user["Enabled"],
    }
