import logging
from fastapi import (
    APIRouter,
    WebSocket,
    Depends,
    Query,
    Path,
    Body,
    HTTPException,
)

from src.app.landing_voicechat.landing_voicechat_websocket_middleware import (
    LandingVoicechatWebsocketMiddleware,
)
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.elevenlabs.enums import WebSocketEventType, FeedbackKey
from src.app.errors import EnvironmentVariablesValueError
from src.app.landing_voicechat.responses import FeedbackResponse

router = APIRouter(prefix="/landing-voicechat", tags=["Landing Voicechat"])
logger = logging.getLogger(__name__)

# Cache for active connections
active_middlewares: dict[str, LandingVoicechatWebsocketMiddleware] = {}

ELEVENLABS_API_KEY = VariablesGrabber().get("ELEVENLABS_API_KEY")
VOICECHAT_ELEVENLABS_AGENT_ID = VariablesGrabber().get("VOICECHAT_ELEVENLABS_AGENT_ID")


def get_voicechat_elevenlabs_middleware(
    voice_id: str = Query(None, description="ElevenLabs voice ID")
) -> LandingVoicechatWebsocketMiddleware:
    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY not configured")
        raise EnvironmentVariablesValueError("ELEVENLABS_API_KEY not configured")
    if not VOICECHAT_ELEVENLABS_AGENT_ID:
        logger.error("VOICECHAT_ELEVENLABS_AGENT_ID not configured")
        raise EnvironmentVariablesValueError(
            "VOICECHAT_ELEVENLABS_AGENT_ID not configured"
        )

    return LandingVoicechatWebsocketMiddleware(
        agent_id=VOICECHAT_ELEVENLABS_AGENT_ID,
        api_key=ELEVENLABS_API_KEY,
        voice_id=voice_id,
    )


@router.websocket("/ws")
async def voicechat_websocket(
    websocket: WebSocket,
    debug: bool = Query(False, description="Enable debug mode"),
    voicechat_elevenlabs_middleware: LandingVoicechatWebsocketMiddleware = Depends(
        get_voicechat_elevenlabs_middleware
    ),
):
    """
    WebSocket endpoint for voice chat using ElevenLabs API

    This endpoint acts as a middleware between the client and ElevenLabs API.
    It forwards messages bidirectionally between the client and ElevenLabs.
    """
    client_id = None

    try:
        # Setup connections (both client and ElevenLabs)
        client_id = await voicechat_elevenlabs_middleware.setup_connections(
            websocket, debug=debug
        )
        active_middlewares[client_id] = voicechat_elevenlabs_middleware

        # Start bidirectional message forwarding
        await voicechat_elevenlabs_middleware.start_forwarding()

    except Exception as e:
        error_message = f"Error in websocket connection: {str(e)}"
        logger.error(error_message)

        try:
            await websocket.send_json(
                {"type": WebSocketEventType.ERROR, "data": {"error": error_message}}
            )
        except Exception:
            pass

    finally:
        # Close all connections if needed
        await voicechat_elevenlabs_middleware.close_all_connections()

        # Clean up
        if client_id and client_id in active_middlewares:
            del active_middlewares[client_id]


@router.post(
    "/conversations/{conversation_id}/feedback", response_model=FeedbackResponse
)
async def send_conversation_feedback_endpoint(
    conversation_id: str = Path(..., description="Conversation ID"),
    key: FeedbackKey = Body(..., embed=True, description="Feedback key"),
) -> FeedbackResponse:
    # send_conversation_feedback(conversation_id, key)
    return FeedbackResponse(
        message=f"Successfully sent feedback ({key}) for conversation {conversation_id}",
        data={"key": key},
    )
