import json
import logging
from typing import Optional, Any

from src.utils.metaclasses import DynamicSingleton
from src.wrappers.aws.exception import AWSException
from src.wrappers.aws.session import Boto3Session
from botocore.config import Config

logger = logging.getLogger(__name__)

DEFAULT_AWS_REGION = "us-east-1"


class BedrockWrapper(metaclass=DynamicSingleton):

    @AWSException.error_handling
    def __init__(
        self,
        credentials: Optional[dict] = None,
        region: Optional[str] = DEFAULT_AWS_REGION,
        read_timeout: Optional[int] = None,
    ):
        config = (
            Config(
                read_timeout=read_timeout,
            )
            if read_timeout
            else Config()
        )
        self.__client = Boto3Session(credentials=credentials).client(
            "bedrock-runtime", region_name=region, config=config
        )

    @AWSException.error_handling
    def invoke_model(
        self,
        model_id: str,
        prompt: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        body_data: dict[str, str | int | float | dict | list | None] = {}
        if "anthropic" in model_id.lower():
            body_data["messages"] = [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ]
        else:
            body_data["prompt"] = prompt
        if params:
            body_data |= params

        body = json.dumps(body_data)
        response = self.__client.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json",
        )
        logger.debug(f"Boto3 response: '{response}'")

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise Exception(f"Error invoking model: {response}")

        response_body = response.get("body").read().decode("utf-8")
        if not response_body:
            raise Exception("Empty response body")
        return json.loads(response_body)

    # Private helper methods can be added here if needed
