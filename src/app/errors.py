class BadRequestError(Exception):
    def __init__(self, msg: str = "Invalid input data"):
        self.msg = msg
        super().__init__(msg)


class UnauthorizedRequestError(Exception):
    def __init__(self, msg: str = "Unauthorized request"):
        self.msg = msg
        super().__init__(msg)


class ForbiddenRequestError(Exception):
    def __init__(self, msg: str = "Forbidden request"):
        self.msg = msg
        super().__init__(msg)


class ItemNotFoundError(Exception):
    def __init__(self, msg: str = "Item not found"):
        self.msg = msg
        super().__init__(msg)


class ItemAlreadyExistsError(Exception):
    def __init__(self, msg: str = "Item already exists"):
        self.msg = msg
        super().__init__(msg)


class ItemAlreadyDeletedError(Exception):
    def __init__(self, msg: str = "Item already deleted"):
        self.msg = msg
        super().__init__(msg)


class ItemAlreadyRestoredError(Exception):
    def __init__(self, msg: str = "Item already restored"):
        self.msg = msg
        super().__init__(msg)


class InvalidAccessTokenException(Exception):
    def __init__(self, msg: str = "Invalid access token"):
        self.msg = msg
        super().__init__(msg)


class MissingAccessTokenException(Exception):
    def __init__(self, msg: str = "Missing access token"):
        self.msg = msg
        super().__init__(msg)


class UserNotFoundError(Exception):
    def __init__(self, msg: str = "User not found"):
        self.msg = msg
        super().__init__(msg)


class InvalidPasswordError(Exception):
    def __init__(self, msg: str = "Invalid password"):
        self.msg = msg
        super().__init__(msg)


class InvalidCredentialsError(Exception):
    def __init__(self, msg: str = "Invalid credentials"):
        self.msg = msg
        super().__init__(msg)


class AssistantFailedError(Exception):
    def __init__(self, msg: str = "Assistant failed"):
        self.msg = msg
        super().__init__(msg)


class AssistantUnknownStatusError(Exception):
    def __init__(self, msg: str = "Assistant unknown status"):
        self.msg = msg
        super().__init__(msg)


class ThreadIsActiveError(Exception):
    def __init__(self, msg: str = "Thread is active"):
        self.msg = msg
        super().__init__(msg)


class RateLimitExceededError(Exception):
    def __init__(self, msg: str = "Rate limit exceeded"):
        self.msg = msg
        super().__init__(msg)


class EnvironmentVariablesValueError(Exception):
    def __init__(self, msg: str = "Environment variables value error"):
        self.msg = msg
        super().__init__(msg)
