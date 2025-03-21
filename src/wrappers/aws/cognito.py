import logging
from typing import Optional

from botocore.config import Config
from botocore.exceptions import ClientError
import jwt

from .errors import CognitoUserNotFoundError
from .exception import AWSException
from .session import Boto3Session
from src.utils.metaclasses import DynamicSingleton

logger = logging.getLogger(__name__)

DEFAULT_REGION = "us-east-1"


class CognitoWrapper(metaclass=DynamicSingleton):

    # Public:
    @AWSException.error_handling
    def __init__(
        self,
        credentials: Optional[dict] = None,
        region: Optional[str] = DEFAULT_REGION,
    ):
        config_data = {}
        if region:
            config_data["region_name"] = region
        config = Config(**config_data)
        self.__client = Boto3Session(credentials=credentials).client(
            "cognito-idp", config=config
        )
        self.__region = region

    @AWSException.error_handling
    def get_username_from_access_token(self, access_token: str) -> str:
        try:
            response = self.__client.get_user(AccessToken=access_token)
            username = response.get("Username")
            if not username:
                raise CognitoUserNotFoundError("Username not found in the token.")
            return username
        except ClientError as e:
            logger.error(f"Error getting user from token: {str(e)}")
            raise e

    @AWSException.error_handling
    def get_username_from_id_token(
        self, id_token: str, user_pool_id: str, client_app_id: str
    ) -> str:
        decoded_token = self.__decode_id_token(id_token, user_pool_id, client_app_id)
        username = decoded_token.get("cognito:username")
        if not username:
            raise CognitoUserNotFoundError("Username not found in the ID token.")

        return username

    @AWSException.error_handling
    def list_users(self, user_pool_id: str):
        try:
            response = self.__client.list_users(
                UserPoolId=user_pool_id,
            )
            return response["Users"]
        except ClientError as e:
            logger.error(f"Error listing users: {str(e)}")
            return []

    @AWSException.error_handling
    def get_user(self, user_pool_id: str, username: str):
        try:
            response = self.__client.admin_get_user(
                UserPoolId=user_pool_id, Username=username
            )
            return response
        except ClientError as e:
            logger.error(f"Error getting user {username}: {str(e)}")
            if "UserNotFound".lower() in str(e).lower():
                raise CognitoUserNotFoundError(f"User {username} not found.")
            else:
                raise e

    @AWSException.error_handling
    def create_user(
        self,
        user_pool_id: str,
        username: str,
        user_attributes: list,
        temporary_password: str,
    ):
        try:
            response = self.__client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                TemporaryPassword=temporary_password,
                UserAttributes=user_attributes,
            )
            return response
        except ClientError as e:
            logger.error(f"Error creating user {username}: {str(e)}")
            return None

    @AWSException.error_handling
    def delete_user(self, user_pool_id: str, username: str):
        try:
            response = self.__client.admin_delete_user(
                UserPoolId=user_pool_id, Username=username
            )
            return response
        except ClientError as e:
            logger.error(f"Error deleting user {username}: {str(e)}")
            raise CognitoUserNotFoundError(f"User {username} not found.")

    # Private:
    def __decode_id_token(
        self, id_token: str, user_pool_id: str, client_app_id: str
    ) -> dict:
        # URL to retrieve the public key for signature verification
        jwks_url = f"https://cognito-idp.{self.__region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        jwks_client = jwt.PyJWKClient(jwks_url)

        # Get the public key for the JWT
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        # Decode and verify the JWT token
        decoded_token = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_app_id,
            issuer=f"https://cognito-idp.{self.__region}.amazonaws.com/{user_pool_id}",
        )
        return decoded_token
