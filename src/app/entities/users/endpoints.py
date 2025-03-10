from fastapi import APIRouter, Body, Query

from src.app import api_responses
from .responses import (
    MultipleUserResponse,
    SingleUserResponse,
    SingleUserUpdateResponse,
)
from .dtos import UserInputDTO
from .resources import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter()


@router.get(
    "/users",
    response_model=MultipleUserResponse | api_responses.BadRequestError,
)
def list_users_endpoint(
    limit: int = Query(default=100, description="Limit of users to retrieve")
) -> MultipleUserResponse:
    users = list_users(limit)
    return MultipleUserResponse(
        message=f"Successfully retrieved the first {limit} users", data=users
    )


@router.post(
    "/users",
    response_model=SingleUserResponse
    | MultipleUserResponse
    | api_responses.BadRequestError,
)
def create_user_endpoint(
    user_data: UserInputDTO | list[UserInputDTO] = Body(
        ...,
        description="User creation data. Allow multiple users creation when a list is provided.",
    ),
) -> SingleUserResponse | MultipleUserResponse:
    raise NotImplementedError("This endpoint is not implemented yet")
    # try:
    #     if isinstance(user_data, list):
    #         data = [create_user(user) for user in user_data]
    #         return MultipleUserResponse(
    #             message="Successfully created users", data=data
    #         )
    #     else:
    #         data = create_user(user_data)
    #         return SingleUserResponse(
    #             message="Successfully created user", data=data
    #         )
    # except InvalidInputData as e:
    #     return api_responses.BadRequestError(
    #         message=f"Invalid request. Error: {e}", data=None
    #     )


@router.get(
    "/users/{username}",
    response_model=SingleUserResponse | api_responses.BadRequestError,
)
def get_user_endpoint(
    username: str,
) -> SingleUserResponse:
    user = get_user(username)
    return SingleUserResponse(message="Successfully retrieved user", data=user)


@router.delete(
    "/users/{username}",
    response_model=SingleUserResponse | api_responses.BadRequestError,
)
def delete_user_endpoint(
    username: str,
) -> SingleUserResponse:
    raise NotImplementedError("This endpoint is not implemented yet")

    # try:
    #     delete_user(username)
    #     return SingleUserResponse(
    #         message="Successfully deleted user", data=None
    #     )
    # except ItemNotFoundError as e:
    #     return api_responses.BadRequestError(
    #         message=f"Invalid request. Error: {e}",
    #         data=None,
    #         status_code=status.HTTP_404_NOT_FOUND,
    #     )


@router.put(
    "/users/{username}",
    response_model=SingleUserUpdateResponse,
)
def update_user_endpoint(
    username: str,
    params: dict = Body(...),
) -> SingleUserUpdateResponse:
    raise NotImplementedError("This endpoint is not implemented yet")
    # updated_user = update_user(username, params)
    # return api_responses.SingleUserUpdateResponse(
    #     message="Successfully updated user",
    #     data=updated_user,
    # )
