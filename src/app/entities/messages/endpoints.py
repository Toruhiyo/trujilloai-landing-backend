from fastapi import APIRouter

from src.app.common.responses import DeleteResponse
from src.app.auth.toolbox import get_username_from_id_token
from .resources import (
    create_message,
    delete_message,
    get_message,
    list_messages,
)
from .responses import (
    MultipleMessagesResponse,
    SingleMessageResponse,
)

router = APIRouter()


@router.get(
    "/conversations/{conversation_id}/messages", response_model=MultipleMessagesResponse
)
def get_messages_endpoint(conversation_id: str):
    messages = list_messages(conversation_id)
    return MultipleMessagesResponse(
        message=f"Fetched {len(messages)} messages for conversation {conversation_id}",
        data=messages,
    )


@router.get(
    "/conversations/{conversation_id}/messages/{message_id}",
    response_model=SingleMessageResponse,
)
def get_message_endpoint(conversation_id: str, message_id: str):
    message = get_message(conversation_id, message_id)
    return SingleMessageResponse(
        message="Message fetched successfully",
        data=message,
    )


# @router.post(
#     "/conversations/{conversation_id}/messages", response_model=SingleMessageResponse
# )
# def create_message_endpoint(conversation_id: str):
#     username = get_username_from_id_token()
#     new_message = create_message(conversation_id, username)
#     return SingleMessageResponse(
#         message="Message created successfully",
#         data=new_message,
#     )


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    response_model=DeleteResponse,
)
def delete_message_endpoint(conversation_id: str, message_id: str):
    delete_message(conversation_id, message_id)
    return DeleteResponse(message="Message deleted successfully")
