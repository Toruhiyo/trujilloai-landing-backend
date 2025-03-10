import logging
from typing import Optional

from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException
from .session import Boto3Session

logger = logging.getLogger(__name__)


class SQSWrapper(metaclass=DynamicSingleton):
    @AWSException.error_handling
    def __init__(self, credentials: dict | None = None):
        self.__client = Boto3Session(credentials=credentials).client("sqs")

    @AWSException.error_handling
    def send_message(
        self, queue_url: str, message_body: str, delay_seconds: int = 0
    ) -> dict:
        logger.info(
            f"Sending message to SQS - Queue URL: '{queue_url}' - Message Body: '{message_body}'"
        )
        response = self.__client.send_message(
            QueueUrl=queue_url, MessageBody=message_body, DelaySeconds=delay_seconds
        )
        logger.debug(f"Boto3 response: '{response}'")
        return response

    @AWSException.error_handling
    def receive_messages(
        self,
        queue_url: str,
        max_number_of_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> list:
        logger.info(f"Receiving messages from SQS - Queue URL: '{queue_url}'")
        messages = self.__client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_number_of_messages,
            WaitTimeSeconds=wait_time_seconds,
        ).get("Messages", [])
        logger.debug(f"Received messages: '{messages}'")
        return messages

    @AWSException.error_handling
    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        logger.debug(
            f"Deleting message from SQS - Queue URL: '{queue_url}' - Receipt Handle: '{receipt_handle}'"
        )
        response = self.__client.delete_message(
            QueueUrl=queue_url, ReceiptHandle=receipt_handle
        )
        logger.debug(f"Boto3 response: '{response}'")
        return True

    @AWSException.error_handling
    def list_queues(self, queue_name_prefix: Optional[str] = None) -> list:
        if queue_name_prefix:
            logger.info(f"Listing SQS queues with prefix: '{queue_name_prefix}'")
        else:
            logger.info("Listing all SQS queues")
        response = self.__client.list_queues(QueueNamePrefix=queue_name_prefix)
        queues = response.get("QueueUrls", [])
        logger.debug(f"Found queues: '{queues}'")
        return queues

    @AWSException.error_handling
    def purge_queue(self, queue_url: str) -> bool:
        logger.debug(f"Purging SQS queue - Queue URL: '{queue_url}'")
        response = self.__client.purge_queue(QueueUrl=queue_url)
        logger.debug(f"Boto3 response: '{response}'")
        return True
