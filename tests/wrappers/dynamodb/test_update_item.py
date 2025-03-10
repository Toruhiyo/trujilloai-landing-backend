from src.wrappers.aws.dynamodb import DynamoDBWrapper


def test_update_str_item():
    table = "test-dynamodb"
    key = {"id": "1234"}
    update_expression = "SET #name = :name"
    expression_attribute_names = {"#name": "name"}
    expression_attribute_values = {":name": "name_updated"}

    item = DynamoDBWrapper().update_item(
        table,
        key,
        update_expression,
        expression_attribute_names,
        expression_attribute_values,
    )

    assert isinstance(item, dict)
    assert item.get("name") == expression_attribute_values.get(":name")


def test_update_add_new_maps_in_list_item():
    new_component = [
        {
            "name": "age",
            "label": "Quin és la teva edat?",
            "type": "AGE_FIELD",
            "initialValue": "",
            "required": True,
        },
        {
            "name": "country",
            "label": "Quin és el teu país?",
            "type": "COUNTRY_FIELD",
            "initialValue": "",
            "required": True,
        },
    ]

    table = "test-dynamodb"
    key = {"id": "1234"}
    update_expression = "SET #components = list_append(components, :map)"
    expression_attribute_names = {"#components": "components"}
    expression_attribute_values = {":map": new_component}

    item = DynamoDBWrapper().update_item(
        table,
        key,
        update_expression,
        expression_attribute_names,
        expression_attribute_values,
    )

    assert isinstance(item, dict)


def test_update_replace_new_maps_in_list_item():
    new_component = [
        {
            "name": "age",
            "label": "Quin és la teva edat?",
            "type": "AGE_FIELD",
            "initialValue": "",
            "required": True,
        },
        {
            "name": "country",
            "label": "Quin és el teu país?",
            "type": "COUNTRY_FIELD",
            "initialValue": "",
            "required": True,
        },
    ]

    table = "test-dynamodb"
    key = {"id": "1234"}
    update_expression = "SET #components = :new_components"
    expression_attribute_names = {"#components": "components"}
    expression_attribute_values = {":new_components": new_component}

    item = DynamoDBWrapper().update_item(
        table,
        key,
        update_expression,
        expression_attribute_names,
        expression_attribute_values,
    )
    assert isinstance(item, dict)
    assert item["components"] == new_component
