import logging
from fastapi import APIRouter, Cookie
from .toolbox import post_message_and_await_reply, generate_session_id
from src.app.chat.dtos import InputMessageDTO
from src.app.entities.messages.responses import SingleMessageResponse


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chatbot/chat", response_model=SingleMessageResponse)
async def post_message_endpoint(
    message: InputMessageDTO, session_id: str = Cookie(None)
) -> SingleMessageResponse:
    logger.info(f"Received message: {message}. Session ID: {session_id}")
    session_id = session_id or generate_session_id()
    reply_message = post_message_and_await_reply(
        message.content, conversation_id=session_id
    )
    return SingleMessageResponse(
        message="Message created successfully", data=reply_message
    )
