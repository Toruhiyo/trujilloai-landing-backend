import logging
from decimal import Decimal
from typing import Optional, Any

from botocore.config import Config
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.aws.exception import AWSException
from src.wrappers.aws.session import Boto3Session
from src.wrappers.aws.errors import DynamodbItemNotFoundError
from src.utils.json_toolbox import make_serializable


logger = logging.getLogger(__name__)

DEFAULT_MAX_POOL_CONNECTIONS = 100


class DynamoDBWrapper(metaclass=DynamicSingleton):

    # Public:
    @AWSException.error_handling
    def __init__(
        self,
        credentials: dict | None = None,
        region: Optional[str] = None,
        max_pool_connections: Optional[int] = DEFAULT_MAX_POOL_CONNECTIONS,
    ):
        config_data = {}
        config_data["max_pool_connections"] = max_pool_connections
        if region:
            config_data["region_name"] = region
        config = Config(**config_data)
        self.__resource = Boto3Session(credentials=credentials).resource(
            "dynamodb", config=config
        )

    @AWSException.error_handling
    def create_item(self, table_name: str, item_data: dict) -> dict:
        item_data = self.__ensure_compatibility(item_data)
        table = self.__resource.Table(table_name)
        response = table.put_item(Item=item_data)
        logger.debug(f"Boto3 response: '{response}'")

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise Exception(f"Failed to create item: {response}")

        return item_data

    @AWSException.error_handling
    def get_item(
        self,
        table_name: str,
        item_key: dict,
        include_fields: Optional[list[str]] = None,
    ) -> dict:
        table = self.__resource.Table(table_name)
        if include_fields:
            projection_expression = ",".join(
                f"#Attribute{i}" for i, _ in enumerate(include_fields)
            )
            expression_attribute_names = {
                f"#Attribute{i}": field for i, field in enumerate(include_fields)
            }
            response = table.get_item(
                Key=item_key,
                ProjectionExpression=projection_expression,
                ExpressionAttributeNames=expression_attribute_names,
            )
        else:
            response = table.get_item(Key=item_key)
        logger.debug(f"Boto3 response: '{response}'")

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise Exception(f"Error getting item: {response}")

        return response.get("Item", None)

    @AWSException.error_handling
    def list_items(
        self,
        table_name: str,
        limit: Optional[int | None] = None,
        include_fields: Optional[list[str]] = None,
    ) -> list[dict]:
        table = self.__resource.Table(table_name)
        items = []
        scan_kwargs: dict[str, str | int | dict | list | None] = (
            {"Limit": limit} if limit else {}
        )

        if include_fields:
            projection_expression = ",".join(
                f"#Attribute{i}" for i, _ in enumerate(include_fields)
            )
            expression_attribute_names = {
                f"#Attribute{i}": field for i, field in enumerate(include_fields)
            }
            scan_kwargs["ProjectionExpression"] = projection_expression
            scan_kwargs["ExpressionAttributeNames"] = expression_attribute_names

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            if "LastEvaluatedKey" not in response or (limit and len(items) >= limit):
                break

            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            if limit:
                # Adjust limit for the next scan if needed
                remaining_limit = limit - len(items)
                if remaining_limit <= 0:
                    break
                scan_kwargs["Limit"] = remaining_limit

        return items[:limit] if limit else items

    @AWSException.error_handling
    def find_items_by_params(
        self,
        table_name: str,
        params: dict,
        valid_keys: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        (
            filter_expression,
            expression_attributes,
            expression_values,
        ) = self.__generate_filter_expression(params, valid_keys=valid_keys)
        return self.find_items(
            table_name,
            filter_expression,
            expression_attributes,
            expression_values,
            limit=limit,
        )

    @AWSException.error_handling
    def find_item_by_params(
        self,
        table_name: str,
        params: dict,
        valid_keys: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> dict | None:
        items = self.find_items_by_params(
            table_name, params, valid_keys=valid_keys, limit=limit
        )
        if not items:
            return None
        return items[0]

    @AWSException.error_handling
    def find_items(
        self,
        table_name: str,
        filter_expression: str,
        expression_attribute_names: dict,
        expression_attribute_values: dict,
        limit: Optional[int] = None,
    ) -> list[dict]:
        config = Config(
            retries={
                "max_attempts": 10,
                "mode": "adaptive",  # Use 'adaptive' mode to automatically handle throttling.
            }
        )
        table = self.__resource.Table(table_name, config=config)
        items = []
        scan_kwargs = {
            "FilterExpression": filter_expression,
            "ExpressionAttributeNames": expression_attribute_names,
            "ExpressionAttributeValues": expression_attribute_values,
        }

        if limit:
            scan_kwargs["Limit"] = limit

        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            # Check if there's more data to retrieve (pagination)
            if "LastEvaluatedKey" not in response or (limit and len(items) >= limit):
                break

            # Continue with pagination
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            if limit:
                remaining_limit = limit - len(items)
                if remaining_limit <= 0:
                    break
                scan_kwargs["Limit"] = remaining_limit

        return items[:limit] if limit else items

    @AWSException.error_handling
    def find_item(
        self,
        table_name: str,
        filter_expression: str,
        expression_attribute_names: dict,
        expression_attribute_values: dict,
        limit: Optional[int] = None,
    ) -> dict | None:
        items = self.find_items(
            table_name,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit=limit,
        )
        if not items:
            return None
        return items[0]

    @AWSException.error_handling
    def update_item(
        self,
        table_name: str,
        item_key: dict,
        update_expression: str,
        expression_attribute_names: dict,
        expression_attribute_values: dict,
    ) -> dict | None:
        table = self.__resource.Table(table_name)
        response = table.update_item(
            Key=item_key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues={
                k: self.__ensure_compatibility(v)
                for k, v in expression_attribute_values.items()
            },
            ReturnValues="UPDATED_NEW",
        )

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise Exception(f"Failed updating item: {response}")

        return response.get("Attributes", None)

    @AWSException.error_handling
    def update_item_from_dict(
        self,
        table_name: str,
        item_key: dict,
        update_data: dict,
        valid_keys: Optional[list[str]] = None,
    ) -> dict | None:
        (
            expression,
            attribute_names,
            attribute_values,
        ) = self.__generate_update_expression(update_data, valid_keys=valid_keys)
        return self.update_item(
            table_name,
            item_key,
            expression,
            attribute_names,
            attribute_values,
        )

    @AWSException.error_handling
    def delete_item(
        self, table_name: str, item_key: dict, check_existence: bool = False
    ) -> dict | None:
        table = self.__resource.Table(table_name)
        if check_existence:
            item = self.get_item(table_name, item_key)
            if not item:
                raise DynamodbItemNotFoundError(f"Item not found: {item_key}")
        response = table.delete_item(Key=item_key)
        logger.debug(f"Boto3 response: '{response}'")

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise Exception(f"Failed deleting item: {response}")

        return response.get("Attributes", None)

    @AWSException.error_handling
    def delete_items_by_params(
        self,
        table_name: str,
        params: dict,
        key_name: str = "id",
        valid_keys: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> None:
        items = self.find_items_by_params(
            table_name, params, valid_keys=valid_keys, limit=limit
        )
        for item in items:
            item_key = {key_name: item[key_name]}
            self.delete_item(table_name, item_key)

    # Private:
    @classmethod
    def __ensure_compatibility(cls, item_data: dict) -> dict:
        return cls.__replace_floats(make_serializable(item_data))

    @classmethod
    def __replace_floats(cls, obj: Any) -> Any:
        """
        Recursively convert all float values to decimal.Decimal values in a data structure.
        This is useful for preparing Python data structures for input into DynamoDB.
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: cls.__replace_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls.__replace_floats(x) for x in obj]
        else:
            return obj

    @classmethod
    def __generate_update_expression(
        cls, params: dict, valid_keys: Optional[list[str]] = None
    ):
        expression_parts = []
        attribute_names = {}
        attribute_values = {}
        params = make_serializable(params)
        for key, value in params.items():
            if isinstance(valid_keys, list) and key not in valid_keys:
                raise ValueError(f"Invalid key: {key}")
            expression_parts.append(f"#{key} = :{key}")
            attribute_names[f"#{key}"] = key
            attribute_values[f":{key}"] = value
        expression = f"SET {', '.join(expression_parts)}"
        return expression, attribute_names, attribute_values

    @classmethod
    def __generate_filter_expression(
        cls, params: dict, valid_keys: Optional[list[str]] = None
    ) -> tuple[str, dict, dict]:
        expression_parts = []
        attribute_names = {}
        attribute_values = {}
        params = make_serializable(params)
        for key, value in params.items():
            if valid_keys and key not in valid_keys:
                raise ValueError(f"Invalid key '{key}'. Valid fields are: {valid_keys}")
            expression_parts.append(f"#{key} = :{key}")
            attribute_names[f"#{key}"] = key
            attribute_values[f":{key}"] = value
        expression = " AND ".join(expression_parts)
        return expression, attribute_names, attribute_values
