import base64


def encode_audio_data(audio_bytes: bytes) -> str:
    """Encode audio data as base64 string for transmission"""
    return base64.b64encode(audio_bytes).decode("utf-8")


def decode_audio_data(audio_base64: str) -> bytes:
    """Decode base64 audio data to bytes"""
    return base64.b64decode(audio_base64)
