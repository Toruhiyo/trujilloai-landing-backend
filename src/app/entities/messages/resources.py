import re
from openai import NotFoundError, BadRequestError
from src.app.entities.conversations.resources import (
    get_conversation,
    get_thread_from_conversation_id,
)
from .enums import RoleType
from .dtos import MessageDTO
from .toolbox import typify_message
from src.wrappers.azure.openai.session import AzureOpenAiSession
from src.app.errors import ItemNotFoundError, ThreadIsActiveError


def list_messages(conversation_id: str) -> list[MessageDTO]:
    conversation = get_conversation(conversation_id)
    thread_messages = AzureOpenAiSession().beta.threads.messages.list(
        thread_id=conversation.id
    )
    return [typify_message(message) for message in thread_messages]


def get_message(conversation_id: str, message_id: str) -> MessageDTO:
    try:
        raw_message = AzureOpenAiSession().beta.threads.messages.retrieve(
            message_id=message_id, thread_id=conversation_id
        )
        return typify_message(raw_message)
    except NotFoundError as e:
        raise ItemNotFoundError(f"No message found with id {message_id}. Details: {e}")


def create_message(
    conversation_id: str, username: str, role: RoleType, content: str
) -> MessageDTO:
    # conversation = get_conversation(conversation_id)
    # thread = get_thread_from_conversation_id(conversation_id, conversation=conversation)
    thread = get_thread_from_conversation_id(conversation_id)
    try:
        message = AzureOpenAiSession().beta.threads.messages.create(
            thread_id=thread.id, role=role.value, content=content
        )
    except BadRequestError as e:
        if hasattr(e, "body") and isinstance(e.body, dict):
            message = e.body.get("message")
            if isinstance(message, str) and re.search(
                r"run_.* is active", message, re.IGNORECASE
            ):
                raise ThreadIsActiveError(
                    f"Thread {thread.id} is active. Please wait for it to finish."
                )
        raise e
    return MessageDTO(
        **{
            "id": message.id,
            "conversation_id": conversation_id,
            "username": username,
            "created_at": message.created_at,
            "role": role,
            "content": content,
        }
    )


def delete_message(conversation_id: str, message_id: str):
    message = get_message(conversation_id, message_id)
    AzureOpenAiSession().beta.threads.messages.delete(
        message_id=message_id, thread_id=conversation_id
    )
    return message


def create_user_thread(username: str) -> str:
    thread = AzureOpenAiSession().beta.threads.create(metadata={"username": username})
    return thread.id
