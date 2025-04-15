class InvalidPromptTemplateError(Exception):
    def __init__(self, msg: str = "Failed to create prompt template"):
        self.msg = msg
        super().__init__(msg)


class InvalidLLMResponseFormatError(Exception):
    def __init__(self, msg: str = "Failed to typify LLM response into expected format"):
        self.msg = msg
        super().__init__(msg)
