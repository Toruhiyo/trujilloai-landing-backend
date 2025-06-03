from src.utils.typification.base_enum import BaseEnum


class AnimationName(str, BaseEnum):
    """Animation names for trigger animations"""

    SALUTE = "salute"
    THUMBSUP = "thumbsup"
    EXAGGERATED_TALKING = "exaggerated_talking"


class AnimationLifecycleWhen(str, BaseEnum):
    """When to trigger the animation during agent state"""

    AGENT_SPEAKING = "agent_speaking"
    AGENT_LISTENING = "agent_listening"
