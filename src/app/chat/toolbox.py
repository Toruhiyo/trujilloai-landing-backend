import uuid
from typing import Optional
from src.app.entities.messages.dtos import MessageDTO
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.aws.bedrock_agent import BedrockAgentWrapper
from src.app.entities.messages.enums import RoleType
from datetime import datetime

AGENT_ID = VariablesGrabber().get("CHATBOT_BEDROCK_AGENT_ID")
AGENT_ALIAS_ID = VariablesGrabber().get("CHATBOT_BEDROCK_AGENT_ALIAS_ID")


def post_message_and_await_reply(
    content: str, conversation_id: Optional[str] = None
) -> MessageDTO:
    reply = BedrockAgentWrapper().invoke(
        agent_id=AGENT_ID,
        agent_alias_id=AGENT_ALIAS_ID,
        input_text=content,
        session_id=conversation_id,
    )
    return MessageDTO(
        **{
            "content": reply,
            "conversation_id": conversation_id,
            "role": RoleType.ASSISTANT,
            "username": "chatbot",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "deleted_at": None,
        }
    )


def generate_session_id() -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "chatbot"))
