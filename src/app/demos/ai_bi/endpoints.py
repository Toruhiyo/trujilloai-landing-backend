import logging
from fastapi import (
    APIRouter,
    WebSocket,
    Depends,
    Query,
    Body,
)

from src.app.demos.ai_bi.aibi_websocket_middleware import (
    AibiWebsocketMiddleware,
)
from src.app.demos.ai_bi.nlq.nlq_agent import AibiNlqAgent
from src.app.demos.ai_bi.responses import NlqResponse
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.elevenlabs.enums import WebSocketEventType
from src.app.errors import EnvironmentVariablesValueError

# Define router with the aibi prefix and appropriate tags
router = APIRouter(prefix="/aibi", tags=["AI BI"])
logger = logging.getLogger(__name__)

# Cache for active connections
active_middlewares: dict[str, AibiWebsocketMiddleware] = {}

ELEVENLABS_API_KEY = VariablesGrabber().get("ELEVENLABS_API_KEY")
DEMO_AIBI_ELEVENLABS_AGENT_ID = VariablesGrabber().get("DEMO_AIBI_ELEVENLABS_AGENT_ID")


def get_aibi_elevenlabs_middleware(
    voice_id: str = Query(None, description="ElevenLabs voice ID")
) -> AibiWebsocketMiddleware:
    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY not configured")
        raise EnvironmentVariablesValueError("ELEVENLABS_API_KEY not configured")
    if not DEMO_AIBI_ELEVENLABS_AGENT_ID:
        logger.error("DEMO_AIBI_ELEVENLABS_AGENT_ID not configured")
        raise EnvironmentVariablesValueError(
            "DEMO_AIBI_ELEVENLABS_AGENT_ID not configured"
        )

    return AibiWebsocketMiddleware(
        agent_id=DEMO_AIBI_ELEVENLABS_AGENT_ID,
        api_key=ELEVENLABS_API_KEY,
        voice_id=voice_id,
    )


@router.websocket("/ws")
async def aibi_websocket(
    websocket: WebSocket,
    debug: bool = Query(False, description="Enable debug mode"),
    aibi_elevenlabs_middleware: AibiWebsocketMiddleware = Depends(
        get_aibi_elevenlabs_middleware
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
        client_id = await aibi_elevenlabs_middleware.setup_connections(
            websocket, debug=debug
        )
        active_middlewares[client_id] = aibi_elevenlabs_middleware

        # Start bidirectional message forwarding
        await aibi_elevenlabs_middleware.start_forwarding()

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
        await aibi_elevenlabs_middleware.close_all_connections()

        # Clean up
        if client_id and client_id in active_middlewares:
            del active_middlewares[client_id]


@router.post("/nlq", response_model=NlqResponse)
async def natural_language_query(
    user_query: str = Body(
        ..., embed=True, description="Natural language query to convert to SQL"
    )
):
    """
    Convert a natural language query to SQL, execute it and return the results
    """
    try:
        nlq_agent = AibiNlqAgent()
        result = nlq_agent.compute(user_query)

        return NlqResponse(
            message="Successfully generated and executed SQL query",
            data=result,
        )
    except Exception as e:
        error_message = f"Error processing natural language query: {str(e)}"
        logger.error(error_message)
        return {
            "success": False,
            "error": error_message,
        }
