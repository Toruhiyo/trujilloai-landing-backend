from src.wrappers.aws.dynamodb import DynamoDBWrapper
from src.wrappers.aws.session import Boto3Session


def test_boto3_session():
    Boto3Session().get_available_services()


def test_dynamodb_connection():
    DynamoDBWrapper()
