from pydantic import BaseModel, Extra


class BaseDTO(BaseModel):
    class Config:
        extra = Extra.forbid

    @property
    def props_keys(self) -> list[str]:
        return list(self.__dict__.keys())

    @property
    def optional_props_keys(self) -> list[str]:
        return [
            k
            for k, v in self.__annotations__.items()
            if str(v).startswith("typing.Optional")
        ]

    @property
    def required_props_keys(self) -> list[str]:
        optional_props_keys = self.optional_props_keys
        return [k for k in self.props_keys if k not in optional_props_keys]

    @property
    def optional_properties(self) -> dict:
        optional_props_keys = self.optional_props_keys
        return {k: v for k, v in self.__dict__.items() if k in optional_props_keys}

    @property
    def required_properties(self) -> dict:
        required_props_keys = self.required_props_keys
        return {k: v for k, v in self.__dict__.items() if k in required_props_keys}
