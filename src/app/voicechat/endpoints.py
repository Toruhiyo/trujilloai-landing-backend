import logging
from fastapi import (
    APIRouter,
    WebSocket,
    Depends,
    HTTPException,
    Query,
)

from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
)
from src.config.vars_grabber import VariablesGrabber
from .enums import WebSocketEventType

router = APIRouter(prefix="/voicechat", tags=["voicechat"])
logger = logging.getLogger(__name__)

# Cache for active connections
active_middlewares: dict[str, ElevenLabsWebsocketMiddleware] = {}

ELEVENLABS_API_KEY = VariablesGrabber().get("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = VariablesGrabber().get("ELEVENLABS_AGENT_ID")


def get_elevenlabs_middleware(
    voice_id: str = Query(None, description="ElevenLabs voice ID")
) -> ElevenLabsWebsocketMiddleware:
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")
    if not ELEVENLABS_AGENT_ID:
        raise HTTPException(
            status_code=500, detail="ELEVENLABS_AGENT_ID not configured"
        )

    return ElevenLabsWebsocketMiddleware(
        agent_id=ELEVENLABS_AGENT_ID, api_key=ELEVENLABS_API_KEY, voice_id=voice_id
    )


@router.websocket("/ws")
async def voicechat_websocket(
    websocket: WebSocket,
    debug: bool = Query(False, description="Enable debug mode"),
    elevenlabs_middleware: ElevenLabsWebsocketMiddleware = Depends(
        get_elevenlabs_middleware
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
        client_id = await elevenlabs_middleware.setup_connections(
            websocket, debug=debug
        )
        active_middlewares[client_id] = elevenlabs_middleware

        # Start bidirectional message forwarding
        await elevenlabs_middleware.start_forwarding()

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
        # Clean up
        if client_id and client_id in active_middlewares:
            del active_middlewares[client_id]

        # Close all connections if needed
        await elevenlabs_middleware.close_all_connections()
