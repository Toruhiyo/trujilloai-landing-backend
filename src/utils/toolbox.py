import os
import json
import logging
from mimetypes import MimeTypes

logger = logging.getLogger(__name__)


def get_path(current_file: str, relative_path: str = "") -> str:
    """
    current_file must be __file__
    """
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), relative_path)


def load_json_file(json_file_path):
    """
    Loads a JSON file content into a dict object.
    :param json_file_path: path to the JSON file
    :return: The dict object with the JSON content
    """

    with open(json_file_path, "r") as json_file:
        content = json.load(json_file)

    return content


def calculate_limit_and_offset(page: int, page_size: int | str, total: int):
    if page_size == "inf":
        limit = total
        offset = 0
    else:
        limit = page_size
        offset = (page - 1) * page_size

    return limit, offset


def iterate_in_batches(lst, batch_size):
    for i in range(0, len(lst), batch_size):
        yield lst[i : i + batch_size]


def load_environment_variable(key):
    try:
        return os.environ[key]
    except KeyError:
        logger.error(f"Environment variable {key} not found")
        raise KeyError(f"Environment variable {key} not found")


def get_content_type(filename: str) -> str:
    mime = MimeTypes()
    content_type, _ = mime.guess_type(filename)
    if content_type is None:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == ".doc":
            content_type = "application/msword"
        elif ext == ".pdf":
            content_type = "application/pdf"
        else:
            content_type = "application/octet-stream"
    return content_type
