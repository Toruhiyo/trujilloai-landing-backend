import logging

from src.utils.exception import GenericException, error_handling

logger = logging.getLogger(__name__)


class ResourceException(GenericException):
    def __init__(self, msg, code=400, data=None):
        self.code = code
        self.data = data if data else {}
        super().__init__(msg)

    @classmethod
    @error_handling
    def error_handling(cls, function):
        def wrapper(*args, **kwargs):
            try:
                response = function(*args, **kwargs)
                return response
            except ResourceException as e:
                raise e
            except GenericException as e:
                raise e
            except Exception as e:
                msg = f"'{function.__name__}' - Unexpected error: '{e}'"
                logger.error(msg)
                raise GenericException(msg)

        wrapper.__name__ = function.__name__
        return wrapper
