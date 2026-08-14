# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import json
import logging
import time
from typing import Optional
from urllib.parse import urlencode

import urllib3

from apple_ads_platform.auth.protocols import ClientSecretProvider
from apple_ads_platform.auth.errors import TokenFetchError
from apple_ads_platform.log_level import LogLevel

auth_logger = logging.getLogger("apple_ads_platform.auth")


class AccessTokenFetcher:

    def __init__(
        self,
        client_id: str,
        secret_provider: ClientSecretProvider,
        http: urllib3.PoolManager,
        auth_base_url: str = "https://appleid.apple.com",
        log_level: Optional[LogLevel] = None,
    ) -> None:
        self._client_id = client_id
        self._secret_provider = secret_provider
        self._token_url = f"{auth_base_url.rstrip('/')}/auth/oauth2/token"
        self._log_level = log_level
        self._http = http

    def fetch_token(self) -> tuple[str, int]:
        client_secret = self._secret_provider.create_secret()

        if self._log_level:
            auth_logger.info("-> POST %s", self._token_url)

        start = time.monotonic()

        try:
            response = self._http.request(
                "POST",
                self._token_url,
                body=urlencode({
                    "grant_type": "client_credentials",
                    "scope": "searchadsorg",
                    "client_id": self._client_id,
                    "client_secret": client_secret,
                }),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            if self._log_level:
                auth_logger.info("<- ERROR POST %s (%.0fms)", self._token_url, elapsed)
            raise TokenFetchError(f"HTTP request to token endpoint failed: {e}") from e

        elapsed = (time.monotonic() - start) * 1000

        if self._log_level:
            auth_logger.info("<- %s POST %s (%.0fms)", response.status, self._token_url, elapsed)
            if self._log_level == LogLevel.HEADERS:
                auth_logger.info("   Headers: %s", dict(response.headers))

        if response.status != 200:
            raise TokenFetchError(
                f"Token endpoint returned status {response.status}: {response.data.decode('utf-8', errors='replace')}"
            )

        try:
            body = json.loads(response.data)
        except (json.JSONDecodeError, ValueError) as e:
            raise TokenFetchError(f"Failed to parse token response JSON: {e}") from e

        access_token = body.get("access_token")
        expires_in = body.get("expires_in")

        if not access_token or expires_in is None:
            raise TokenFetchError(
                f"Token response missing required fields: {list(body.keys())}"
            )

        return access_token, int(expires_in)
