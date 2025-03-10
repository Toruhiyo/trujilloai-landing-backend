import logging
from pathlib import Path
from typing import Callable, Optional
from uuid import NAMESPACE_URL, uuid5

logger = logging.getLogger(__name__)


class CacheManager:
    # Public:
    def __init__(
        self, base_cache_directory: Path, version_name: str = "undefined"
    ) -> None:
        self.__base_cache_directory = base_cache_directory
        self.__cache_directory = self.__base_cache_directory / version_name
        self.__cache_directory.mkdir(parents=True, exist_ok=True)

    def get_or_set(self, prompt: str, func: Callable[[], str]) -> str:
        key = self.__prompt2key(prompt)
        cached = self.get_by_key(key)
        if isinstance(cached, str):
            logger.info(f"Cache hit for {key}.")
            return cached
        try:
            result = func()
            self.set_by_key(key, result)
            return result
        except Exception as e:
            logger.warning(
                f"Failed to compute {key}. Results not cached. Details: {type(e)}-{e}."
            )
            raise e

    def get_by_prompt(self, prompt: str) -> Optional[str]:
        return self.get_by_key(self.__prompt2key(prompt))

    def get_by_key(self, key: str) -> Optional[str]:
        cache_file = self.__cache_directory / key
        if cache_file.exists():
            return cache_file.read_text()
        return None

    def set_by_prompt(self, prompt: str, value: str) -> None:
        self.set_by_key(self.__prompt2key(prompt), value)

    def set_by_key(self, key: str, value: str) -> None:
        cache_file = self.__cache_directory / key
        cache_file.write_text(value)
        logger.info(f"Cache set for {key}.")

    # Private:
    def __prompt2key(self, prompt: str) -> str:
        # remove any non-alphanumeric characters
        prompt = "".join([c for c in prompt if c.isalnum() or c == " "])
        # replace any whitespace with a single space
        prompt = " ".join(prompt.split())
        return str(uuid5(NAMESPACE_URL, prompt))
