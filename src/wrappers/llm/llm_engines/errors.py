class StoppedByLength(Exception):
    pass


class InvalidRequest(Exception):
    pass


class ExceededMaxLength(Exception):
    def __init__(
        self, n_tokens: int | None = None, max_tokens: int | None = None, **kwargs
    ) -> None:
        msg = "Maximum length exceeded."
        msg = f"{msg} n_tokens={n_tokens}" if n_tokens is not None else msg
        msg = f"{msg} max_tokens={max_tokens}" if max_tokens is not None else msg
        super().__init__(msg, **kwargs)


class NoRelevantData(Exception):
    pass


class FailedExtractingData(Exception):
    pass


class TextCompletionFailed(Exception):
    pass


class BatchIsSmallerThanAllowed(Exception):
    pass
