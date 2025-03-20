import logging
import os

from boto3.session import Session

from src.config.vars_grabber import VariablesGrabber
from src.config.scopes import ScopeType
from ...utils.metaclasses import DynamicSingleton
from .exception import AWSException

logger = logging.getLogger(__name__)

# Default region to use if none is specified
DEFAULT_REGION = "us-east-1"


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
            # Ensure region is set in credentials dict
            if "region_name" not in params:
                params["region_name"] = self.__get_region()
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

            # Always ensure region is set
            params["region_name"] = self.__get_region()

            if (
                VariablesGrabber().get(
                    "AWS_PROFILE", scopes=ScopeType.LOCAL, ignore_missing_keys=True
                )
                is not None
            ):
                params["profile_name"] = VariablesGrabber().get("AWS_PROFILE")

        logger.info(
            f"Initializing AWS Session with region: {params.get('region_name', 'UNKNOWN')}"
        )
        super().__init__(**params)

    def __get_region(self) -> str:
        """
        Get the AWS region from environment variables in the following order:
        1. AWS_REGION (direct env var)
        2. AWS_DEFAULT_REGION (direct env var)
        3. From VariablesGrabber (which may read from .env file)
        4. Default to DEFAULT_REGION constant
        """
        # Direct environment variable access first (highest priority)
        if region := os.environ.get("AWS_REGION"):
            return region

        if region := os.environ.get("AWS_DEFAULT_REGION"):
            return region

        # Then try through VariablesGrabber
        if region := VariablesGrabber().get(
            "AWS_DEFAULT_REGION",
            scopes=ScopeType.LOCAL,
            ignore_missing_keys=True,
        ):
            return region

        # Fall back to default
        logger.warning(
            f"No AWS region found in environment variables, using default: {DEFAULT_REGION}"
        )
        return DEFAULT_REGION
