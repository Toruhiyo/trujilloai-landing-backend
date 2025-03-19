import uuid


def generate_session_id() -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "chatbot"))
