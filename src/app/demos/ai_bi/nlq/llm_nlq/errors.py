class InvalidLLMResponseFormatError(Exception):
    def __init__(
        self, msg: str = "Failed to typify LLM response into expected SQL query format"
    ):
        self.msg = msg
        super().__init__(msg)


class SqlExecutionError(Exception):
    def __init__(self, msg: str = "Error executing SQL query"):
        self.msg = msg
        super().__init__(msg)


class UnsafeQueryError(Exception):
    def __init__(self, msg: str = "Query contains unsafe operations"):
        self.msg = msg
        super().__init__(msg)
