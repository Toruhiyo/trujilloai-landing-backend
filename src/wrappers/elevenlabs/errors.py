class ToolCallMissingParametersError(Exception):
    def __init__(self, tool_name: str, missing_parameters: list[str]):
        self.tool_name = tool_name
        self.missing_parameters = missing_parameters
        super().__init__(
            f"Tool call {tool_name} missing parameters: {missing_parameters}"
        )
