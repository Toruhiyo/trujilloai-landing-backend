import pytz
from datetime import datetime
from src.config.vars_grabber import VariablesGrabber


TIMESTAMP_FORMAT = VariablesGrabber().get(
    "DYNAMODB_ITEMS_TIMESTAMP_FORMAT", default="%Y-%m-%dT%H:%M:%S.%fZ", type=str
)


def get_current_utc_timestamp() -> str:
    return datetime.now(pytz.UTC).strftime(TIMESTAMP_FORMAT)
