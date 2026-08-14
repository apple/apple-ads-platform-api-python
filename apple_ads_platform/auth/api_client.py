# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import logging
import time
from typing import Optional

from importlib.metadata import version, PackageNotFoundError

from apple_ads_platform.api_client import ApiClient
from apple_ads_platform.auth.protocols import AccessTokenProvider
from apple_ads_platform.log_level import LogLevel
from apple_ads_platform.configuration import Configuration
from apple_ads_platform import rest


def _resolve_version() -> str:
    try:
        return version("apple-ads-platform")
    except PackageNotFoundError:
        from apple_ads_platform import __version__
        return __version__


_USER_AGENT = f"apple-ads-python-{_resolve_version()}"

api_logger = logging.getLogger("apple_ads_platform.api")

_REDACTED_HEADERS = {"Authorization"}


def _redact_headers(headers: dict) -> dict:
    return {
        k: "[REDACTED]" if k in _REDACTED_HEADERS else v
        for k, v in headers.items()
    }


class AuthenticatedApiClient(ApiClient):

    def __init__(
        self,
        access_token_provider: AccessTokenProvider,
        configuration: Configuration,
        log_level: Optional[LogLevel] = None,
    ) -> None:
        super().__init__(configuration)
        self._access_token_provider = access_token_provider
        self._log_level = log_level

    def call_api(
        self,
        method,
        url,
        header_params=None,
        body=None,
        post_params=None,
        _request_timeout=None,
    ) -> rest.RESTResponse:
        if header_params is None:
            header_params = {}
        header_params["Authorization"] = f"Bearer {self._access_token_provider.get_token()}"
        header_params["User-Agent"] = _USER_AGENT

        if self._log_level:
            self._log_request(method, url, header_params, body)

        start = time.monotonic()
        try:
            response = super().call_api(
                method, url, header_params, body, post_params, _request_timeout
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            if self._log_level:
                api_logger.info("<- ERROR %s %s (%.0fms)", method, url, elapsed)
            raise

        elapsed = (time.monotonic() - start) * 1000
        if self._log_level:
            self._log_response(method, url, response, elapsed)

        return response

    def _log_request(self, method: str, url: str, headers: dict, body) -> None:
        api_logger.info("-> %s %s", method, url)
        if self._log_level in (LogLevel.HEADERS, LogLevel.BODY):
            api_logger.info("   Headers: %s", _redact_headers(headers))
        if self._log_level == LogLevel.BODY and body is not None:
            api_logger.info("   Body: %s", body)

    def _log_response(
        self, method: str, url: str, response: rest.RESTResponse, elapsed_ms: float
    ) -> None:
        api_logger.info("<- %s %s %s (%.0fms)", response.status, method, url, elapsed_ms)
        if self._log_level in (LogLevel.HEADERS, LogLevel.BODY):
            api_logger.info("   Headers: %s", dict(response.headers))
        if self._log_level == LogLevel.BODY:
            data = response.read() if hasattr(response, "read") else response.data
            if data is not None:
                api_logger.info("   Body: %s", data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data)
