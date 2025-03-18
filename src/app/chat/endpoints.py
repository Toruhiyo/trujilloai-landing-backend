import logging
from fastapi import APIRouter, Cookie, Body, Path
from .resources import post_message_and_await_reply, generate_session_id
from src.app.chat.dtos import InputMessageDTO, HighlightRequestDTO
from src.app.entities.messages.responses import SingleMessageResponse
from src.app.chat.responses import HighlightTextResponseDTO

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


@router.post("/chatbot/chat/{session_id}/highlight")
async def highlight_endpoint(
    session_id: str = Path(...), highlight_request: HighlightRequestDTO = Body(...)
) -> HighlightTextResponseDTO:
    logger.info(
        f"Received highlight request for session ID: {session_id}. Text to highlight: {highlight_request.text}. Section: {highlight_request.section}"
    )
    return HighlightTextResponseDTO(
        message="Highlight request received", data=highlight_request.text
    )
