from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from .enums import MessageRole, WebSocketEventType


class PromptDTO(BaseModel):
    """Prompt configuration for the agent"""

    prompt: str


class AgentConfigDTO(BaseModel):
    """Agent configuration"""

    prompt: PromptDTO
    first_message: Optional[str] = None
    language: str = "en"


class TTSConfigDTO(BaseModel):
    """Text-to-speech configuration"""

    voice_id: str


class ConversationConfigDTO(BaseModel):
    """Conversation configuration"""

    agent: AgentConfigDTO
    tts: TTSConfigDTO


class CustomLLMExtraBodyDTO(BaseModel):
    """Custom LLM configuration"""

    temperature: float = 0.7
    max_tokens: int = 150


class ConversationInitiationDTO(BaseModel):
    """Conversation initiation data from client"""

    type: str = WebSocketEventType.CONVERSATION_INITIATION
    conversation_config_override: ConversationConfigDTO
    custom_llm_extra_body: Optional[CustomLLMExtraBodyDTO] = None
    dynamic_variables: Optional[Dict[str, Any]] = None


class AudioChunkDTO(BaseModel):
    """Audio chunk from user"""

    user_audio_chunk: str  # base64 encoded audio


class PongDTO(BaseModel):
    """Pong response to server ping"""

    type: str = WebSocketEventType.PONG
    event_id: int


class ClientToolResultDTO(BaseModel):
    """Result of a tool call"""

    type: str = WebSocketEventType.CLIENT_TOOL_RESULT
    tool_call_id: str
    result: Any
    is_error: bool = False
