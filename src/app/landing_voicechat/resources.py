from src.wrappers.elevenlabs.elevenlabs_client import ElevenlabsClient
from src.wrappers.elevenlabs.enums import FeedbackKey
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

elevenlabs_client = ElevenlabsClient()


def send_conversation_feedback(conversation_id: str, key: FeedbackKey):
    try:
        elevenlabs_client.conversational_ai.post_conversation_feedback(
            conversation_id=conversation_id,
            feedback=str(key),
        )
    except HTTPException as e:
        logger.error(f"Error sending conversation feedback: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error sending conversation feedback: {e}")
        raise e
