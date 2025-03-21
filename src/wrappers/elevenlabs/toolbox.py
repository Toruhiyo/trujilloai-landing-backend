from elevenlabs.client import ElevenLabs


def get_signed_url(api_key: str, agent_id: str):
    try:
        client = ElevenLabs(api_key=api_key)
        response = client.conversational_ai.get_signed_url(agent_id=agent_id)
        return response.signed_url
    except Exception as error:
        print(f"Error getting signed URL: {error}")
        raise
