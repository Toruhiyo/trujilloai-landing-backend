from src.wrappers.aws.dynamodb import DynamoDBWrapper


def test_get_item():
    table = "test-dynamodb"
    key = {"id": "1234"}
    item = DynamoDBWrapper().get_item(table, key)
    assert isinstance(item, dict)
