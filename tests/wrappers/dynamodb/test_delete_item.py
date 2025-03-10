from src.wrappers.aws.dynamodb import DynamoDBWrapper


def test_delete_item():
    table = "test-dynamodb"
    key = {"id": "1234"}
    item = DynamoDBWrapper().delete_item(table, key)
    assert isinstance(item, bool)
