from src.config.vars_grabber import VariablesGrabber
from src.wrappers.aws.cognito import CognitoWrapper

DEFAULT_USER_POOL_ID = VariablesGrabber().get("AWS_COGNITO_USER_POOL_ID")
DEFAULT_CLIENT_APP_ID = VariablesGrabber().get("AWS_COGNITO_CLIENT_APP_ID")


def get_username_from_id_token(
    token: str,
    user_pool_id: str = DEFAULT_USER_POOL_ID,
    client_app_id: str = DEFAULT_CLIENT_APP_ID,
) -> str:
    return CognitoWrapper().get_username_from_id_token(
        token, user_pool_id, client_app_id
    )
