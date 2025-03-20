from botocore.exceptions import ClientError
import logging
from typing import Generator, Any

import boto3

from src.wrappers.aws.secrets_manager import SecretsManagerWrapper
from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException

logger = logging.getLogger(__name__)

DEFAULT_REGION = "us-east-1"


class SSMWrapper(metaclass=DynamicSingleton):
    @AWSException.error_handling
    def __init__(self, credentials: dict | None = None, region: str | None = None):
        self.__client = (
            boto3.Session(**credentials).client("ssm")
            if credentials
            else boto3.client("ssm", region_name=region or DEFAULT_REGION)
        )

    # @AWSException.error_handling
    def get_parameter(self, name: str) -> dict[str, Any]:
        return self.__client.get_parameter(Name=name, WithDecryption=True)["Parameter"]

    # @AWSException.error_handling
    def get_secret(self, name: str) -> dict[str, Any]:
        try:
            return self.__client.get_parameter(Name=name, WithDecryption=True)[
                "Parameter"
            ]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return SecretsManagerWrapper().get_secret(name)
            raise e

    @AWSException.error_handling
    def get_parameters_names(self) -> list[str]:
        paginator = self.__client.get_paginator("describe_parameters")
        return [
            param["Name"]
            for page in paginator.paginate()
            for param in page["Parameters"]
        ]

    @AWSException.error_handling
    def get_secrets_names(self) -> list[str]:
        return SecretsManagerWrapper().list_secrets()

    @AWSException.error_handling
    def existing_parameters_generator(self) -> Generator[dict[str, Any], None, None]:
        paginator = self.__client.get_paginator("describe_parameters")
        for page in paginator.paginate():
            for param in page["Parameters"]:
                yield self.get_parameter(param["Name"])

    @AWSException.error_handling
    def delete_all_parameters(self):
        names = self.get_parameters_names()
        for name in names:
            self.delete_parameter(name)

    @AWSException.error_handling
    def push_parameter(self, name: str, value: str, type: str = "String"):
        return self.__client.put_parameter(
            Name=name, Value=value, Type=type, Overwrite=False
        )

    @AWSException.error_handling
    def push_secret(self, name: str, value: str, type: str = "SecureString"):
        return self.push_parameter(name, value, type)

    @AWSException.error_handling
    def update_secret(self, name: str, value: str, type: str = "SecureString"):
        return self.__client.put_parameter(
            Name=name, Value=value, Type=type, Overwrite=True
        )

    @AWSException.error_handling
    def delete_parameter(self, name: str):
        return self.__client.delete_parameter(Name=name)
