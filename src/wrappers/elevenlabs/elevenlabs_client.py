from src.config.vars_grabber import VariablesGrabber
from src.utils.metaclasses import DynamicSingleton
from elevenlabs import ElevenLabs

DEFAULT_API_KEY = VariablesGrabber().get("ELEVENLABS_API_KEY")


class ElevenlabsClient(ElevenLabs, metaclass=DynamicSingleton):
    def __init__(self, api_key: str = DEFAULT_API_KEY):
        super().__init__(api_key=api_key)
