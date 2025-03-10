from enum import Enum


class ModelType(Enum):
    GPT3 = "GPT-3"
    BLOOM = "BLOOM"
    BLOOMZ = "BLOOMZ"
    GPT = "GPT4"
    MOCK = "MOCK"
    null = "null"

    def __str__(self) -> str:
        return self.value
