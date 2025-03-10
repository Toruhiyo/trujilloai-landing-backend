from src.wrappers.aws.dynamodb import DynamoDBWrapper


def test_get_all_item():
    table = "test-dynamodb"
    items = DynamoDBWrapper().list_items(table)
    assert isinstance(items, list)
    assert isinstance(items[0], dict)
