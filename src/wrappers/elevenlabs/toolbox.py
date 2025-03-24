from elevenlabs.client import ElevenLabs
from copy import deepcopy


def get_signed_url(api_key: str, agent_id: str):
    try:
        client = ElevenLabs(api_key=api_key)
        response = client.conversational_ai.get_signed_url(agent_id=agent_id)
        return response.signed_url
    except Exception as error:
        print(f"Error getting signed URL: {error}")
        raise


def format_message_for_logging(message: dict) -> dict:
    message_copy = deepcopy(message)
    if message_copy.get("audio_event"):
        message_copy["audio_event"] = "..."
    if message_copy.get("user_audio_chunk"):
        message_copy["user_audio_chunk"] = "..."
    return message_copy
