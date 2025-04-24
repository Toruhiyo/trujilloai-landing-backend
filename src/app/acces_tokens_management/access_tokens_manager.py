from datetime import datetime, timedelta
import secrets
import logging

from .dtos import AccessToken
from src.utils.metaclasses import DynamicSingleton

logger = logging.getLogger(__name__)


class AccessTokensManager(metaclass=DynamicSingleton):
    def __init__(self, scope: str, token_expiry_minutes: int = 5):
        self.__scope = scope
        self.__tokens: dict[str, AccessToken] = {}
        self.__token_expiry_minutes = token_expiry_minutes
        self.__cleanup_interval = timedelta(minutes=1)
        self.__last_cleanup = datetime.now()

    # Public:
    @property
    def scope(self) -> str:
        return self.__scope

    @property
    def tokens(self) -> dict[str, AccessToken]:
        return self.__tokens

    def generate_token(self, ip: str) -> str:
        self.__cleanup_expired_tokens()

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=self.__token_expiry_minutes)

        self.__tokens[ip] = AccessToken(token=token, expires_at=expires_at)

        return token

    def validate_token(self, ip: str, token: str) -> bool:
        self.__cleanup_expired_tokens()

        if ip not in self.__tokens:
            return False

        token_data = self.__tokens[ip]

        if token_data.expires_at < datetime.now():
            del self.__tokens[ip]
            return False

        if token_data.token != token:
            return False

        del self.__tokens[ip]  # Token is single-use
        return True

    def revoke_token(self, ip: str) -> None:
        if ip in self.__tokens:
            del self.__tokens[ip]

    # Private:
    def __cleanup_expired_tokens(self) -> None:
        current_time = datetime.now()
        if current_time - self.__last_cleanup < self.__cleanup_interval:
            return

        expired_ips = [
            ip for ip, data in self.__tokens.items() if data.expires_at < current_time
        ]

        for ip in expired_ips:
            del self.__tokens[ip]

        self.__last_cleanup = current_time
        if expired_ips:
            logger.debug(f"Cleaned up {len(expired_ips)} expired tokens")
