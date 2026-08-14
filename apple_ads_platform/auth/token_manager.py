# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import logging
import threading
import time
from typing import Optional

from apple_ads_platform.auth.errors import TokenFetchError
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher

logger = logging.getLogger("apple_ads_platform.auth")

_REFRESH_BUFFER_SECONDS = 60
_MIN_EXPIRY_FOR_BUFFER = 90
_RETRY_DELAY_SECONDS = 30


class TokenManager:

    def __init__(self, token_fetcher: AccessTokenFetcher) -> None:
        self._fetcher = token_fetcher
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._closed = False

        self.refresh_token()

    def get_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._expires_at:
                return self._token

        return self.refresh_token()

    def refresh_token(self) -> str:
        with self._lock:
            token, expires_in = self._fetcher.fetch_token()
            self._token = token
            self._expires_at = time.time() + expires_in
            self._schedule_refresh(expires_in)
            return token

    def close(self) -> None:
        self._closed = True
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def __enter__(self) -> "TokenManager":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _schedule_refresh(self, expires_in: int) -> None:
        if self._closed:
            return

        if self._timer:
            self._timer.cancel()

        if expires_in < _MIN_EXPIRY_FOR_BUFFER:
            delay = expires_in / 2
        else:
            delay = expires_in - _REFRESH_BUFFER_SECONDS

        timer = threading.Timer(delay, self._background_refresh)
        timer.daemon = True
        timer.start()
        self._timer = timer

    def _background_refresh(self) -> None:
        if self._closed:
            return

        try:
            self.refresh_token()
            logger.debug("Background token refresh succeeded")
        except TokenFetchError:
            logger.warning(
                "Background token refresh failed, scheduling retry in %ds",
                _RETRY_DELAY_SECONDS,
            )
            if not self._closed:
                timer = threading.Timer(
                    _RETRY_DELAY_SECONDS, self._background_refresh
                )
                timer.daemon = True
                timer.start()
                self._timer = timer
