class InvalidOrCorruptedFile(Exception):
    def __init__(
        self,
        msg: str = "The file is invalid or corrupted",
    ):
        self.msg = msg
        super().__init__(msg)
