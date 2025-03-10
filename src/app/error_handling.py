import logging
import traceback

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .errors import (
    BadRequestError,
    ForbiddenRequestError,
    InvalidAccessTokenException,
    ItemAlreadyDeletedError,
    ItemAlreadyExistsError,
    ItemAlreadyRestoredError,
    ItemNotFoundError,
    MissingAccessTokenException,
    ThreadIsActiveError,
    UnauthorizedRequestError,
    UserNotFoundError,
)
from .exception import ResourceException

logger = logging.getLogger(__name__)


def set_app_exception_handlers(app):
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ):
        errors = set(
            [
                f"{', '.join(map(str, err['loc']))} - {err['msg']}"
                for err in exc.errors()
            ]
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": f"Invalid request. {'. '.join(errors)}",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            },
        )

    @app.exception_handler(ResourceException)
    async def handle_form_exception(request: Request, exc: ResourceException):
        return JSONResponse(
            status_code=exc.code,
            content={"message": exc.msg, "status_code": exc.code, "data": exc.data},
        )

    @app.exception_handler(NotImplementedError)
    async def handle_not_implemented_error(request: Request, exc: NotImplementedError):
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "message": str(exc),
                "status_code": status.HTTP_501_NOT_IMPLEMENTED,
            },
        )

    @app.exception_handler(BadRequestError)
    async def handle_bad_request(request: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": str(exc),
                "status_code": status.HTTP_400_BAD_REQUEST,
            },
        )

    @app.exception_handler(UnauthorizedRequestError)
    async def handle_unauthorized_request(
        request: Request, exc: UnauthorizedRequestError
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": str(exc), "status_code": status.HTTP_401_UNAUTHORIZED},
        )

    @app.exception_handler(ForbiddenRequestError)
    async def handle_forbidden_request(request: Request, exc: ForbiddenRequestError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": str(exc),
                "status_code": status.HTTP_403_FORBIDDEN,
            },
        )

    @app.exception_handler(ThreadIsActiveError)
    async def handle_thread_is_active(request: Request, exc: ThreadIsActiveError):
        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={"message": str(exc), "status_code": status.HTTP_423_LOCKED},
        )

    @app.exception_handler(ItemNotFoundError)
    async def handle_item_not_found(request: Request, exc: ItemNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": str(exc),
                "status_code": status.HTTP_404_NOT_FOUND,
            },
        )

    @app.exception_handler(ItemAlreadyExistsError)
    async def handle_item_already_exists(request: Request, exc: ItemAlreadyExistsError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": str(exc), "status_code": status.HTTP_409_CONFLICT},
        )

    @app.exception_handler(ItemAlreadyDeletedError)
    async def handle_item_already_deleted(
        request: Request, exc: ItemAlreadyDeletedError
    ):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": str(exc),
                "status_code": status.HTTP_200_OK,
            },
        )

    @app.exception_handler(ItemAlreadyRestoredError)
    async def handle_item_already_restored(
        request: Request, exc: ItemAlreadyRestoredError
    ):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": str(exc),
                "status_code": status.HTTP_200_OK,
            },
        )

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(request: Request, exc: UserNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": str(exc),
                "status_code": status.HTTP_404_NOT_FOUND,
            },
        )

    @app.exception_handler(MissingAccessTokenException)
    async def handle_missing_access_token(
        request: Request, exc: MissingAccessTokenException
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": str(exc),
                "status_code": status.HTTP_403_FORBIDDEN,
            },
        )

    @app.exception_handler(InvalidAccessTokenException)
    async def handle_invalid_access_token(
        request: Request, exc: MissingAccessTokenException
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "message": str(exc),
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        logger.error(
            f"Unexpected error in request {request.method} {request.url}: {exc}. "
            f"Traceback: {traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Unexpected error",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )

    app.add_exception_handler(NotImplementedError, handle_not_implemented_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(ResourceException, handle_form_exception)
    app.add_exception_handler(BadRequestError, handle_bad_request)
    app.add_exception_handler(UnauthorizedRequestError, handle_unauthorized_request)
    app.add_exception_handler(ForbiddenRequestError, handle_forbidden_request)
    app.add_exception_handler(ThreadIsActiveError, handle_thread_is_active)
    app.add_exception_handler(ItemNotFoundError, handle_item_not_found)
    app.add_exception_handler(ItemAlreadyExistsError, handle_item_already_exists)
    app.add_exception_handler(ItemAlreadyDeletedError, handle_item_already_deleted)
    app.add_exception_handler(ItemAlreadyRestoredError, handle_item_already_restored)
    app.add_exception_handler(UserNotFoundError, handle_user_not_found)
    app.add_exception_handler(MissingAccessTokenException, handle_missing_access_token)
    app.add_exception_handler(InvalidAccessTokenException, handle_invalid_access_token)
    app.add_exception_handler(Exception, handle_generic_exception)
