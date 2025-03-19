from typing import Optional
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.aws.bedrock_agent import BedrockAgentWrapper
from src.app.errors import RateLimitExceededError
from src.wrappers.aws.errors import RateLimitExceededError as AWSRateLimitExceededError
from .dtos import ChatbotBotMessageDTO
from .toolbox import generate_session_id

AGENT_ID = VariablesGrabber().get("CHATBOT_BEDROCK_AGENT_ID")
AGENT_ALIAS_ID = VariablesGrabber().get("CHATBOT_BEDROCK_AGENT_ALIAS_ID")


def post_message_and_await_reply(
    content: str, conversation_id: Optional[str] = None
) -> ChatbotBotMessageDTO:
    conversation_id = conversation_id or generate_session_id()
    try:
        reply = BedrockAgentWrapper().invoke(
            agent_id=AGENT_ID,
            agent_alias_id=AGENT_ALIAS_ID,
            input_text=content,
            session_id=conversation_id,
        )
    except AWSRateLimitExceededError:
        raise RateLimitExceededError()
    return ChatbotBotMessageDTO(
        content=reply["text"],
        conversation_id=conversation_id,
    )
