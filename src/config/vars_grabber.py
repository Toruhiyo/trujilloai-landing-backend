import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Optional

from src.wrappers.aws.ssm import SSMWrapper
from src.config.scopes import ScopeType
from ..utils.metaclasses import DynamicSingleton
import logging

logger = logging.getLogger(__name__)

DEFAULT_ENV_PATH = Path(".env")
BASE_MANDATORY_VARS = ["ENV", "PROJECT_KEY"]

DEFAULT_AWS_REGION = "us-east-1"


class VariablesGrabber(metaclass=DynamicSingleton):
    def __init__(
        self,
        env_path: Path = DEFAULT_ENV_PATH,
        extra_mandatory_vars: Optional[list[str]] = None,
        aws_region: Optional[str] = None,
    ):
        extra_mandatory_vars = extra_mandatory_vars or []
        self.__env_path = env_path
        self.__mandatory_vars = BASE_MANDATORY_VARS + extra_mandatory_vars
        self.__environment = os.environ.get("ENV")
        if not self.__environment or (
            isinstance(self.__environment, str)
            and self.__environment.lower() == "local"
        ):
            self.__load_dot_env()
        self.__validate_mandatory_vars()
        aws_region = aws_region or os.environ.get("AWS_REGION") or DEFAULT_AWS_REGION
        self.__ssm = SSMWrapper(region=aws_region)

    def get(
        self,
        name: str,
        ignore_missing_keys: Optional[bool] = False,
        scopes: Optional[list[ScopeType] | ScopeType] = None,
        type: Any = str,
        default: Optional[Any] = None,
        can_be_none: bool = True,
    ) -> Any:
        try:
            value = self.__retrieve_variable(
                name, ignore_missing_keys=ignore_missing_keys, scopes=scopes
            )
        except Exception as e:
            if default is not None or can_be_none:
                value = default
            else:
                raise e
        return (
            self.__cast_value(value, type, can_be_none=can_be_none) if value else value
        )

    # Private:
    def __load_dot_env(self):
        if not self.__env_path.exists():
            raise FileNotFoundError(".env file is missing")
        load_dotenv(dotenv_path=self.__env_path)

    def __validate_mandatory_vars(self):
        for var in self.__mandatory_vars:
            if not os.getenv(var):
                raise ValueError(f"Variable {var} is missing in .env file")

        self.__environment = os.environ["ENV"]
        self.__project_key = os.environ["PROJECT_KEY"]

    def __retrieve_variable(
        self,
        name: str,
        ignore_missing_keys: Optional[bool] = False,
        scopes: Optional[list[ScopeType] | ScopeType] = None,
    ) -> Any:

        scopes = (
            [scopes] if isinstance(scopes, ScopeType) else scopes or list(ScopeType)
        )
        if ScopeType.LOCAL in scopes and (value := os.getenv(name)):
            return value

        if ScopeType.AWS in scopes:
            # Construct the full path for the SSM parameter or secret
            full_path = f"/{self.__project_key}/{self.__environment}/{name}"

            # Try to get it from SSM (assuming it could be either a parameter or a secret)
            try:
                parameter = self.__ssm.get_parameter(full_path)
                return parameter["Value"]
            except Exception as e:
                logger.debug(f"Error retrieving parameter: {e}")

            try:
                secret = self.__ssm.get_secret(full_path)
                return secret["Value"]
            except Exception as e:
                logger.debug(f"Error retrieving secret: {e}")

        if ignore_missing_keys:
            return None
        raise ValueError(
            f"Variable {name} not found in .env, AWS Parameter Store, or Secrets Manager"
        )

    def __cast_value(self, value: str, type: Any, can_be_none: bool = True) -> Any:
        if type is bool:
            return value.lower() in ["true", "1"]
        elif type is Path:
            return Path(value)
        elif type is list:
            return [self.__cast_value(v, str) for v in value.split(",")]
        elif type is dict:
            return {k: self.__cast_value(v, str) for k, v in value.split(",")}
        elif type is tuple:
            return tuple(self.__cast_value(v, str) for v in value.split(","))
        elif type is float:
            return float(value)
        elif type is int:
            return int(value)

        if can_be_none and value.lower() == "none" or value == "null" or value == "":
            return None
        return type(value)
