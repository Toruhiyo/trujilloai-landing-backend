import logging
from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)


def get_signed_url(api_key: str, agent_id: str):
    """
    Get a signed URL from ElevenLabs for websocket connections.

    Args:
        api_key: ElevenLabs API key
        agent_id: ElevenLabs Agent ID

    Returns:
        Signed URL for websocket connection
    """
    try:
        logger.info(f"Getting signed URL for agent ID: {agent_id}")
        if not api_key:
            logger.error("API key is empty or None")
            raise ValueError("API key is required")

        if not agent_id:
            logger.error("Agent ID is empty or None")
            raise ValueError("Agent ID is required")

        # Log masked API key for debugging (only first 4 and last 4 chars)
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
        logger.info(f"Using API key: {masked_key}")

        client = ElevenLabs(api_key=api_key)
        logger.info("Created ElevenLabs client, requesting signed URL...")

        response = client.conversational_ai.get_signed_url(agent_id=agent_id)

        if not response or not response.signed_url:
            logger.error("Received empty signed URL from ElevenLabs")
            raise Exception("Received empty signed URL from ElevenLabs")

        logger.info("Successfully received signed URL from ElevenLabs")
        return response.signed_url
    except Exception as error:
        logger.error(f"Error getting signed URL: {error}")
        # Re-raise to allow calling code to handle
        raise
