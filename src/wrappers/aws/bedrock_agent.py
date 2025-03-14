import json
import logging
import time
from typing import Optional, Any

from botocore.exceptions import ClientError
from botocore.eventstream import EventStream
from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException
from .errors import RateLimitExceededError
from .session import Boto3Session

logger = logging.getLogger(__name__)


class BedrockAgentWrapper(metaclass=DynamicSingleton):

    # Public:
    @AWSException.error_handling
    def __init__(self, credentials: dict | None = None, region: Optional[str] = None):
        config_data = {}
        if region:
            config_data["region_name"] = region

        self.__client = Boto3Session(credentials=credentials).client(
            "bedrock-agent-runtime", config=config_data if config_data else None
        )

    @AWSException.error_handling
    def invoke(
        self,
        agent_id: str,
        agent_alias_id: str,
        input_text: str,
        session_id: Optional[str] = None,
        enable_trace: bool = False,
        memory_attributes: Optional[dict[str, Any]] = None,
        end_session: bool = False,
        max_attempts: int = 3,
        retry_delay: float = 2.0,
    ) -> str:
        self.__client.meta.config.retries = {"max_attempts": max_attempts}

        request_body = {
            "inputText": input_text,
            "enableTrace": enable_trace,
        }

        if session_id:
            request_body["sessionId"] = session_id

        if memory_attributes:
            request_body["memoryAttributes"] = memory_attributes

        if end_session:
            request_body["endSession"] = end_session

        attempts = 0
        last_exception = None

        while attempts < max_attempts:
            try:
                attempts += 1
                response = self.__client.invoke_agent(
                    agentId=agent_id, agentAliasId=agent_alias_id, **request_body
                )

                # Process the streaming response if needed
                completion = self.__process_response(response)
                return completion

            except ClientError as e:
                last_exception = e
                code = e.response["Error"]["Code"]
                message = e.response["Error"]["Message"]

                if (
                    code == "throttlingException"
                    and "rate is too high" in message.lower()
                ):
                    last_exception = RateLimitExceededError(message)
                    if attempts <= max_attempts:
                        wait_time = retry_delay * (
                            2 ** (attempts - 1)
                        )  # Exponential backoff
                        logger.info(
                            f"Rate limit exceeded, retrying in {wait_time:.2f} seconds (attempt {attempts}/{max_attempts})"
                        )
                        time.sleep(wait_time)
                        continue
                # Check if this is the "not in ready state" error
                if (
                    code == "validationException"
                    and "not in ready state" in message.lower()
                ):

                    if attempts <= max_attempts:
                        wait_time = retry_delay * (
                            2 ** (attempts - 1)
                        )  # Exponential backoff
                        logger.info(
                            f"Agent not ready, retrying in {wait_time:.2f} seconds (attempt {attempts}/{max_attempts})"
                        )
                        time.sleep(wait_time)
                        continue

                # For other errors or if we've exhausted retries
                logger.error(f"Bedrock Agent invocation failed: {code} - {message}")
                raise e

        # If we've exhausted all retries
        if last_exception:
            logger.error(f"Bedrock Agent still not ready after {max_attempts} attempts")
            raise last_exception

    @AWSException.error_handling
    def list_agents(self) -> list:
        response = self.__client.list_agents()
        return response.get("agentSummaries", [])

    @AWSException.error_handling
    def get_agent(self, agent_id: str) -> dict:
        response = self.__client.get_agent(agentId=agent_id)
        return response

    # Private:
    def __process_response(self, response) -> str:
        """Process the EventStream response from Bedrock Agent and return just the completion text."""
        completion_event = response.get("completion", None)
        if isinstance(completion_event, EventStream):
            # Handle streaming response
            completion_text = ""
            n_chunks = 0
            for event in completion_event:
                chunk = event.get("chunk", {})
                if chunk and "bytes" in chunk:
                    try:
                        chunk = chunk["bytes"].decode("utf-8")
                        completion_text += chunk
                        n_chunks += 1
                    except json.JSONDecodeError:
                        raise ValueError("Failed to decode chunk data as JSON")
                    except Exception as e:
                        raise ValueError(f"Error processing chunk: {str(e)}")
            logger.info(f"Completion text: {completion_text}. No. chunks: {n_chunks}")
            return completion_text
        else:
            # Handle non-streaming response (though this is less common)
            logger.warning("Received non-streaming response from Bedrock Agent")
            if isinstance(response, dict):
                return response.get("completion", "")
            raise ValueError(
                f"Received invalid response from Bedrock Agent: {response}."
            )
