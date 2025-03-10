import logging
from functools import wraps
from time import perf_counter, sleep
from typing import Any, Callable, Sequence, Type

logger = logging.getLogger(__name__)


def timing(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        name = f.__qualname__
        t0 = perf_counter()
        result = f(*args, **kwargs)
        t1 = perf_counter()
        print(f"{name} - elapsed time: {round(t1-t0, 2)}s.")
        return result

    return wrapper


def retry(
    *args,
    n_attempts: int = 3,
    wait_time: int = 60,
    retry_exceptions: Sequence[Type[Exception]] | None = None,
    raise_exceptions: Sequence[Type[Exception]] | None = None,
    **kwargs,
):
    if raise_exceptions is None:
        raise_exceptions = []

    def wrapper(f: Callable) -> Callable:
        def retry_function(*args, **kwargs):
            for i in range(0, n_attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    if retry_exceptions is not None:
                        for exception in retry_exceptions:
                            if isinstance(e, exception):
                                logger.warning(
                                    f"Failed execution of {f.__qualname__}. Attempt: {i+1}/{n_attempts}. DETAILS: <{str(e)}>"
                                )
                                if i + 1 < n_attempts:
                                    sleep(wait_time)
                                    continue
                                else:
                                    raise e
                    for exception in raise_exceptions:
                        if isinstance(e, exception):
                            raise e
                    logger.warning(
                        f"Failed execution of {f.__qualname__}. Attempt: {i+1}/{n_attempts}. DETAILS: <{str(e)}>"
                    )

        return retry_function

    return wrapper


def print_function(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        name = f.__qualname__
        print(name)
        return f(*args, **kwargs)

    return wrapper


def do_if_true(
    action: Callable = lambda: False,
) -> Callable:
    def wrapper(f: Callable) -> Any:
        def do_if_true_function(*args, **kwargs) -> Callable:
            output = f(*args, **kwargs)
            if output:
                action()
            return output

        return do_if_true_function

    return wrapper
