from src.utils.typification.base_dto import BaseDTO


class AiToolDataDTO(BaseDTO):
    name: str | None
    url: str | None
    summary: str | None
