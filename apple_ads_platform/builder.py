# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import urllib3

from apple_ads_platform.api.apple_ads_api import AppleAdsApi
from apple_ads_platform.auth.api_client import AuthenticatedApiClient
from apple_ads_platform.auth.client_secret import EphemeralClientSecretProvider
from apple_ads_platform.auth.protocols import AccessTokenProvider, ClientSecretProvider
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher
from apple_ads_platform.auth.token_manager import TokenManager
from apple_ads_platform.configuration import Configuration
from apple_ads_platform.log_level import LogLevel

_DEFAULT_BASE_URL = "https://api.ads.apple.com/v1"
_DEFAULT_AUTH_BASE_URL = "https://appleid.apple.com"
_DEFAULT_TIMEOUT = 5.0

_BUILDER_INTERNAL_TOKEN = object()


class InvalidBuilderConfigurationError(ValueError):
    pass


class _AuthMode(Enum):
    PRIVATE_KEY = "private_key"
    CLIENT_SECRET_PROVIDER = "client_secret_provider"
    ACCESS_TOKEN_PROVIDER = "access_token_provider"


class AppleAdsClientBuilder:

    def __init__(self, _internal_token: object = None) -> None:
        if _internal_token is not _BUILDER_INTERNAL_TOKEN:
            raise InvalidBuilderConfigurationError(
                "AppleAdsClientBuilder cannot be instantiated directly; "
                "use one of the AppleAdsClientBuilder.from_* class methods."
            )
        self._mode: Optional[_AuthMode] = None
        self._client_id: Optional[str] = None
        self._team_id: Optional[str] = None
        self._key_id: Optional[str] = None
        self._private_key_pem: Optional[str] = None
        self._client_secret_provider: Optional[ClientSecretProvider] = None
        self._access_token_provider: Optional[AccessTokenProvider] = None
        self._base_url: str = _DEFAULT_BASE_URL
        self._auth_base_url: str = _DEFAULT_AUTH_BASE_URL
        self._api_timeout: float = _DEFAULT_TIMEOUT
        self._api_log_level: Optional[LogLevel] = None
        self._api_proxy: Optional[str] = None
        self._api_proxy_headers: Optional[dict] = None
        self._auth_timeout: float = _DEFAULT_TIMEOUT
        self._auth_log_level: Optional[LogLevel] = None
        self._auth_proxy: Optional[str] = None
        self._auth_proxy_headers: Optional[dict] = None

    @classmethod
    def from_private_key(
        cls,
        client_id: str,
        team_id: str,
        key_id: str,
        private_key: str,
    ) -> AppleAdsClientBuilder:
        if not client_id:
            raise InvalidBuilderConfigurationError("client_id must not be empty")
        if not team_id:
            raise InvalidBuilderConfigurationError("team_id must not be empty")
        if not key_id:
            raise InvalidBuilderConfigurationError("key_id must not be empty")
        if not private_key:
            raise InvalidBuilderConfigurationError("private_key must not be empty")
        b = cls(_BUILDER_INTERNAL_TOKEN)
        b._mode = _AuthMode.PRIVATE_KEY
        b._client_id = client_id
        b._team_id = team_id
        b._key_id = key_id
        b._private_key_pem = private_key
        return b

    @classmethod
    def from_private_key_path(
        cls,
        client_id: str,
        team_id: str,
        key_id: str,
        path: str,
    ) -> AppleAdsClientBuilder:
        if not path:
            raise InvalidBuilderConfigurationError("path must not be empty")
        try:
            pem = Path(path).read_text(encoding="utf-8")
        except (OSError, IOError) as e:
            raise InvalidBuilderConfigurationError(
                f"Failed to read private key from path: {e}"
            ) from e
        return cls.from_private_key(client_id, team_id, key_id, pem)

    @classmethod
    def from_client_secret_provider(
        cls,
        client_id: str,
        provider: ClientSecretProvider,
    ) -> AppleAdsClientBuilder:
        if not client_id:
            raise InvalidBuilderConfigurationError("client_id must not be empty")
        if provider is None:
            raise InvalidBuilderConfigurationError("provider must not be None")
        b = cls(_BUILDER_INTERNAL_TOKEN)
        b._mode = _AuthMode.CLIENT_SECRET_PROVIDER
        b._client_id = client_id
        b._client_secret_provider = provider
        return b

    @classmethod
    def from_access_token_provider(
        cls,
        provider: AccessTokenProvider,
    ) -> AppleAdsClientBuilder:
        if provider is None:
            raise InvalidBuilderConfigurationError("provider must not be None")
        b = cls(_BUILDER_INTERNAL_TOKEN)
        b._mode = _AuthMode.ACCESS_TOKEN_PROVIDER
        b._access_token_provider = provider
        return b

    def base_url(self, url: str) -> AppleAdsClientBuilder:
        self._base_url = url
        return self

    def auth_base_url(self, url: str) -> AppleAdsClientBuilder:
        self._reject_if_access_token_provider_mode("auth_base_url")
        self._auth_base_url = url
        return self

    def api_timeout(self, seconds: float) -> AppleAdsClientBuilder:
        self._api_timeout = seconds
        return self

    def api_log_level(self, level: Optional[LogLevel]) -> AppleAdsClientBuilder:
        if level is not None and not isinstance(level, LogLevel):
            raise InvalidBuilderConfigurationError(
                f"Invalid api_log_level '{level}'. Must be a LogLevel enum value: "
                f"{', '.join(e.value for e in LogLevel)}"
            )
        self._api_log_level = level
        return self

    def api_proxy(self, url: str) -> AppleAdsClientBuilder:
        self._api_proxy = url
        return self

    def api_proxy_headers(self, headers: dict) -> AppleAdsClientBuilder:
        self._api_proxy_headers = headers
        return self

    def auth_timeout(self, seconds: float) -> AppleAdsClientBuilder:
        self._reject_if_access_token_provider_mode("auth_timeout")
        self._auth_timeout = seconds
        return self

    def auth_log_level(self, level: Optional[LogLevel]) -> AppleAdsClientBuilder:
        self._reject_if_access_token_provider_mode("auth_log_level")
        if level is not None and level == LogLevel.BODY:
            raise InvalidBuilderConfigurationError(
                "auth_log_level 'BODY' is forbidden — would log credentials"
            )
        if level is not None and not isinstance(level, LogLevel):
            raise InvalidBuilderConfigurationError(
                f"Invalid auth_log_level '{level}'. Must be a LogLevel enum value: "
                f"{', '.join(e.value for e in LogLevel)}"
            )
        self._auth_log_level = level
        return self

    def auth_proxy(self, url: str) -> AppleAdsClientBuilder:
        self._reject_if_access_token_provider_mode("auth_proxy")
        self._auth_proxy = url
        return self

    def auth_proxy_headers(self, headers: dict) -> AppleAdsClientBuilder:
        self._reject_if_access_token_provider_mode("auth_proxy_headers")
        self._auth_proxy_headers = headers
        return self

    def build(self) -> AppleAdsApi:
        self._validate_inputs()
        token_provider = self._resolve_access_token_provider()
        configuration = self._build_configuration()
        api_client = AuthenticatedApiClient(
            token_provider, configuration, log_level=self._api_log_level
        )
        return AppleAdsApi(api_client)

    def _validate_inputs(self) -> None:
        if self._auth_proxy_headers is not None and self._auth_proxy is None:
            raise InvalidBuilderConfigurationError(
                "auth_proxy_headers requires auth_proxy to be set"
            )

        if self._api_proxy_headers is not None and self._api_proxy is None:
            raise InvalidBuilderConfigurationError(
                "api_proxy_headers requires api_proxy to be set"
            )

    def _reject_if_access_token_provider_mode(self, field: str) -> None:
        if self._mode == _AuthMode.ACCESS_TOKEN_PROVIDER:
            raise InvalidBuilderConfigurationError(
                f"'{field}' is not applicable when the builder is created via "
                f"from_access_token_provider: {field} is only used to build the default "
                f"AccessTokenProvider, which is bypassed when an AccessTokenProvider is provided"
            )

    def _resolve_access_token_provider(self) -> AccessTokenProvider:
        if self._mode == _AuthMode.ACCESS_TOKEN_PROVIDER:
            return self._access_token_provider

        if self._mode == _AuthMode.CLIENT_SECRET_PROVIDER:
            secret_provider = self._client_secret_provider
        else:
            secret_provider = EphemeralClientSecretProvider(
                self._client_id,
                self._team_id,
                self._key_id,
                self._private_key_pem,
            )

        fetcher = AccessTokenFetcher(
            client_id=self._client_id,
            secret_provider=secret_provider,
            http=self._build_auth_http_client(),
            auth_base_url=self._auth_base_url,
            log_level=self._auth_log_level,
        )

        return TokenManager(fetcher)

    def _build_auth_http_client(self) -> urllib3.PoolManager:
        timeout = urllib3.Timeout(connect=self._auth_timeout, read=self._auth_timeout)
        if self._auth_proxy is not None:
            return urllib3.ProxyManager(
                self._auth_proxy,
                proxy_headers=self._auth_proxy_headers,
                timeout=timeout,
            )
        return urllib3.PoolManager(timeout=timeout)

    def _build_configuration(self) -> Configuration:
        configuration = Configuration(host=self._base_url)

        if self._api_timeout != _DEFAULT_TIMEOUT:
            configuration.request_timeout = self._api_timeout

        if self._api_proxy is not None:
            configuration.proxy = self._api_proxy
            if self._api_proxy_headers is not None:
                configuration.proxy_headers = self._api_proxy_headers

        return configuration
