import logging
import traceback
from fastapi import (
    APIRouter,
    WebSocket,
    Depends,
    HTTPException,
    Query,
)
from fastapi.responses import JSONResponse

from src.wrappers.elevenlabs.elevenlabs_websocket_middleware import (
    ElevenLabsWebsocketMiddleware,
)
from src.config.vars_grabber import VariablesGrabber
from .enums import WebSocketEventType
from src.wrappers.elevenlabs.toolbox import get_signed_url

router = APIRouter(prefix="/voicechat", tags=["voicechat"])
logger = logging.getLogger(__name__)

# Cache for active connections
active_middlewares: dict[str, ElevenLabsWebsocketMiddleware] = {}

ELEVENLABS_API_KEY = VariablesGrabber().get("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = VariablesGrabber().get("ELEVENLABS_AGENT_ID")


def get_elevenlabs_middleware(
    voice_id: str = Query(None, description="ElevenLabs voice ID")
) -> ElevenLabsWebsocketMiddleware:
    # Log environment variable status for debugging
    logger.info(f"ELEVENLABS_API_KEY configured: {bool(ELEVENLABS_API_KEY)}")
    logger.info(f"ELEVENLABS_AGENT_ID configured: {bool(ELEVENLABS_AGENT_ID)}")

    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY not configured")
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")
    if not ELEVENLABS_AGENT_ID:
        logger.error("ELEVENLABS_AGENT_ID not configured")
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

    # Accept the connection first to avoid 500 errors
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
    except Exception as accept_error:
        logger.error(f"Failed to accept WebSocket connection: {str(accept_error)}")
        return

    try:
        logger.info("WebSocket connection attempt received")

        # Setup connections (both client and ElevenLabs)
        client_id = await elevenlabs_middleware.setup_connections(
            websocket, debug=debug
        )
        active_middlewares[client_id] = elevenlabs_middleware

        # Start bidirectional message forwarding
        logger.info(f"Starting message forwarding for client: {client_id}")
        await elevenlabs_middleware.start_forwarding()

    except Exception as e:
        error_message = f"Error in websocket connection: {str(e)}"
        stack_trace = traceback.format_exc()
        logger.error(f"{error_message}\n{stack_trace}")

        try:
            # Since we've already accepted the connection, send a useful error message
            await websocket.send_json(
                {
                    "type": WebSocketEventType.ERROR,
                    "data": {
                        "error": error_message,
                        "suggestion": "Check the server logs for more details. "
                        "The issue may be related to ElevenLabs configuration.",
                    },
                }
            )
        except Exception as send_error:
            logger.error(f"Failed to send error to client: {str(send_error)}")

    finally:
        # Clean up
        if client_id and client_id in active_middlewares:
            logger.info(f"Removing client {client_id} from active middlewares")
            del active_middlewares[client_id]

        # Close all connections if needed
        await elevenlabs_middleware.close_all_connections()


@router.get("/health")
async def voicechat_health_check():
    """
    Health check endpoint for the voicechat service.
    Verifies that the ElevenLabs integration is configured correctly.
    """
    response_data = {"status": "error", "message": "", "details": {}}

    # Check if environment variables are set
    response_data["details"]["environment"] = {
        "ELEVENLABS_API_KEY": bool(ELEVENLABS_API_KEY),
        "ELEVENLABS_AGENT_ID": bool(ELEVENLABS_AGENT_ID),
    }

    # Return early if environment variables are missing
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        response_data["message"] = "Missing required environment variables"
        return JSONResponse(status_code=500, content=response_data)

    # Try to get a signed URL from ElevenLabs
    try:
        # We don't need to store the URL, just check if we can get one
        get_signed_url(ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID)
        response_data["status"] = "ok"
        response_data["message"] = "ElevenLabs integration is working correctly"
        return JSONResponse(status_code=200, content=response_data)
    except Exception as e:
        # Log the error
        logger.error(f"ElevenLabs health check failed: {str(e)}")
        response_data["message"] = f"Failed to get signed URL from ElevenLabs: {str(e)}"
        return JSONResponse(status_code=500, content=response_data)
