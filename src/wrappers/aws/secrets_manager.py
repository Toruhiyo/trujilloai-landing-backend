import logging
import boto3
import os

from typing import Generator, Any

from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException

logger = logging.getLogger(__name__)

DEFAULT_REGION = "us-east-1"


class SecretsManagerWrapper(metaclass=DynamicSingleton):
    @AWSException.error_handling
    def __init__(self, credentials: dict | None = None, region: str | None = None):
        # Try to get the region in this order:
        # 1. Directly passed region parameter
        # 2. AWS_REGION environment variable
        # 3. AWS_DEFAULT_REGION environment variable
        # 4. DEFAULT_REGION constant
        region_name = (
            region
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or DEFAULT_REGION
        )

        logger.info(f"Initializing SecretsManager client with region: {region_name}")

        self.__client = (
            boto3.Session(**credentials).client(
                "secretsmanager", region_name=region_name
            )
            if credentials
            else boto3.client("secretsmanager", region_name=region_name)
        )

    # @AWSException.error_handling
    def get_secret(self, secret_id: str) -> dict[str, Any]:
        response = self.__client.get_secret_value(SecretId=secret_id)
        return {
            "ARN": response["ARN"],
            "Name": response["Name"],
            "Value": response["SecretString"],
        }

    @AWSException.error_handling
    def list_secrets(self) -> list[str]:
        paginator = self.__client.get_paginator("list_secrets")
        return [
            secret["Name"]
            for page in paginator.paginate()
            for secret in page["SecretList"]
        ]

    @AWSException.error_handling
    def secrets_generator(self) -> Generator[dict[str, Any], None, None]:
        paginator = self.__client.get_paginator("list_secrets")
        for page in paginator.paginate():
            for secret in page["SecretList"]:
                yield self.get_secret(secret["ARN"])

    @AWSException.error_handling
    def delete_secret(self, secret_id: str, recovery_window_in_days: int = 7):
        return self.__client.delete_secret(
            SecretId=secret_id, RecoveryWindowInDays=recovery_window_in_days
        )

    @AWSException.error_handling
    def put_secret(self, name: str, secret_string: str):
        return self.__client.create_secret(Name=name, SecretString=secret_string)

    @AWSException.error_handling
    def update_secret(self, secret_id: str, new_secret_string: str):
        return self.__client.update_secret(
            SecretId=secret_id, SecretString=new_secret_string
        )
