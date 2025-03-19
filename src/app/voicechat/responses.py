from typing import Dict, Any, Optional
from pydantic import BaseModel
from .enums import WebSocketEventType


class ConversationInitiationMetadataResponse(BaseModel):
    """Initial metadata response from server"""

    type: str = WebSocketEventType.CONVERSATION_INITIATION_METADATA
    conversation_initiation_metadata_event: Dict[str, Any]


class UserTranscriptResponse(BaseModel):
    """User transcript response"""

    type: str = WebSocketEventType.USER_TRANSCRIPT
    user_transcription_event: Dict[str, Any]


class AgentResponseEvent(BaseModel):
    """Agent response event data"""

    type: str = WebSocketEventType.AGENT_RESPONSE
    agent_response_event: Dict[str, str]


class AudioResponse(BaseModel):
    """Audio response from agent"""

    type: str = WebSocketEventType.AUDIO
    audio_event: Dict[str, Any]


class PingResponse(BaseModel):
    """Ping from server"""

    type: str = WebSocketEventType.PING
    ping_event: Dict[str, Any]


class ClientToolCallResponse(BaseModel):
    """Tool call request from server"""

    type: str = WebSocketEventType.CLIENT_TOOL_CALL
    client_tool_call: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response for middleware"""

    type: str = WebSocketEventType.ERROR
    error: str
    details: Optional[Dict[str, Any]] = None
