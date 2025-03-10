import json
import logging
from time import sleep

from botocore.exceptions import ClientError

from .errors import MaxRetriesExceededError

from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException
from .session import Boto3Session

logger = logging.getLogger(__name__)


class LambdaWrapper(metaclass=DynamicSingleton):

    # Public:
    @AWSException.error_handling
    def __init__(self):
        self.__client = Boto3Session().client("lambda")

    @AWSException.error_handling
    def invoke(
        self,
        function_name: str,
        payload: dict,
        read_timeout: int = 60,
        connect_timeout: int = 60,
        max_attempts: int = 3,
        max_idle_attempts: int = 30,
        wait_time: int = 3,
    ):
        try:
            return self.__execute_sync_invocation(
                function_name,
                payload,
                read_timeout=read_timeout,
                connect_timeout=connect_timeout,
                max_attempts=max_attempts,
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]
            if code == "CodeArtifactUserPendingException":
                logger.warning(
                    f"AWS Lambda failed with ClientError and will be retried (max. retries: {max_idle_attempts}). {code} - {message}"
                )
                for i in range(1, max_idle_attempts):
                    sleep(wait_time)
                    try:
                        return self.__execute_sync_invocation(
                            function_name,
                            payload,
                            read_timeout=read_timeout,
                            connect_timeout=connect_timeout,
                            max_attempts=max_attempts,
                        )
                    except ClientError as e:
                        code = e.response["Error"]["Code"]
                        message = e.response["Error"]["Message"]
                        if i >= max_idle_attempts - 1:
                            raise MaxRetriesExceededError(
                                f"AWS Lambda Error - Exceeded maximum number of retries for CodeArtifactUserPendingException ({max_idle_attempts}) with errors: {code} - {message}.",
                            )
                        elif code == "CodeArtifactUserPendingException":
                            logger.warning(
                                f"({i}/{max_idle_attempts}) - AWS Lambda failed. {code} - {message}"
                            )
                        else:
                            raise e
            else:
                raise e

    @AWSException.error_handling
    def async_invoke(
        self,
        function_name: str,
        payload: dict,
        read_timeout: int = 60,
        connect_timeout: int = 60,
        max_attempts: int = 3,
    ) -> str:
        self.__client.meta.config.read_timeout = read_timeout
        self.__client.meta.config.connect_timeout = connect_timeout
        self.__client.meta.config.retries = {"max_attempts": max_attempts}
        response = self.__client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        return response["ResponseMetadata"]["RequestId"]

    @AWSException.error_handling
    def list_functions(self):
        response = self.__client.list_functions()
        return response["Functions"]

    @AWSException.error_handling
    def list_functions_names(self):
        response = self.__client.list_functions()
        return [function["FunctionName"] for function in response["Functions"]]

    @AWSException.error_handling
    def get_function(self, function_name):
        response = self.__client.get_function(FunctionName=function_name)
        return response["Configuration"]

    # Private:
    @AWSException.error_handling
    def __execute_sync_invocation(
        self,
        function_name: str,
        payload: dict,
        read_timeout: int = 60,
        connect_timeout: int = 60,
        max_attempts: int = 3,
    ) -> dict:
        self.__client.meta.config.read_timeout = read_timeout
        self.__client.meta.config.connect_timeout = connect_timeout
        self.__client.meta.config.retries = {"max_attempts": max_attempts}
        response = self.__client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        content_string = response["Payload"].read().decode()
        content = json.loads(content_string)
        return content
