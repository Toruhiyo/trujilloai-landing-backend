import logging

from boto3.session import Session

from src.config.vars_grabber import VariablesGrabber
from src.config.scopes import ScopeType
from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException

logger = logging.getLogger(__name__)


class Boto3Session(Session, metaclass=DynamicSingleton):
    @AWSException.error_handling
    def __init__(self, credentials: dict | None = None):
        """
        Initializes a boto3 session with the credentials found in AWS config variables.
        Only uses SESSION_TOKEN (for Lambda) or DEFAULT_REGION if they are set.

        :return: The boto3 session object
        """
        if isinstance(credentials, dict):
            params = credentials
            params["region_name"] = VariablesGrabber().get(
                "AWS_DEFAULT_REGION", scopes=ScopeType.LOCAL
            )
        else:
            params = {}
            if (
                VariablesGrabber().get(
                    "AWS_ACCESS_KEY_ID",
                    scopes=ScopeType.LOCAL,
                    ignore_missing_keys=True,
                )
                is not None
                and VariablesGrabber().get(
                    "AWS_SECRET_ACCESS_KEY",
                    scopes=ScopeType.LOCAL,
                    ignore_missing_keys=True,
                )
                is not None
                and VariablesGrabber().get(
                    "AWS_SESSION_TOKEN",
                    scopes=ScopeType.LOCAL,
                    ignore_missing_keys=True,
                )
                is not None
            ):
                params["aws_access_key_id"] = VariablesGrabber().get(
                    "AWS_ACCESS_KEY_ID"
                )
                params["aws_secret_access_key"] = VariablesGrabber().get(
                    "AWS_SECRET_ACCESS_KEY"
                )
                params["aws_session_token"] = VariablesGrabber().get(
                    "AWS_SESSION_TOKEN"
                )
            if (
                VariablesGrabber().get(
                    "AWS_DEFAULT_REGION",
                    scopes=ScopeType.LOCAL,
                    ignore_missing_keys=True,
                )
                is not None
            ):
                params["region_name"] = VariablesGrabber().get("AWS_DEFAULT_REGION")
            if (
                VariablesGrabber().get(
                    "AWS_PROFILE", scopes=ScopeType.LOCAL, ignore_missing_keys=True
                )
                is not None
            ):
                params["profile_name"] = VariablesGrabber().get("AWS_PROFILE")

        super().__init__(**params)
