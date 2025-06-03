from src.utils.typification.base_enum import BaseEnum


class AnimationName(str, BaseEnum):
    """Animation names for trigger animations"""

    SALUTE = "salute"
    THUMBSUP = "thumbsup"


class AnimationLifecycle(str, BaseEnum):
    """Animation lifecycle types"""

    ONCE = "once"
    LOOP = "loop"
