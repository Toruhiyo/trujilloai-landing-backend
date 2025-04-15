from src.utils.typification.base_enum import BaseEnum


class WebSocketEventType(str, BaseEnum):
    """Event types for the websocket connection with ElevenLabs"""

    # Client to server events
    CONVERSATION_INITIATION = "conversation_initiation_client_data"
    USER_AUDIO_CHUNK = "user_audio_chunk"
    PONG = "pong"
    CLIENT_TOOL_RESULT = "client_tool_result"

    # Server to client events
    CONVERSATION_INITIATION_METADATA = "conversation_initiation_metadata"
    USER_TRANSCRIPT = "user_transcript"
    AGENT_RESPONSE = "agent_response"
    AGENT_RESPONSE_CORRECTION = "agent_response_correction"
    AUDIO = "audio"
    INTERRUPTION = "interruption"
    PING = "ping"
    CLIENT_TOOL_CALL = "client_tool_call"

    # Internal events
    INTERNAL_VAD_SCORE = "internal_vad_score"
    INTERNAL_TURN_PROBABILITY = "internal_turn_probability"
    INTERNAL_TENTATIVE_AGENT_RESPONSE = "internal_tentative_agent_response"

    # Connection events (for our middleware)
    CONNECTED = "connected"
    ERROR = "error"


class MessageRole(str, BaseEnum):
    """Message roles for ElevenLabs conversation"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FeedbackKey(str, BaseEnum):
    """Feedback keys for conversation feedback"""

    LIKE = "like"
    DISLIKE = "dislike"
