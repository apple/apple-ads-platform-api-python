# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
from apple_ads_platform.auth.protocols import AccessTokenProvider, ClientSecretProvider
from apple_ads_platform.auth.errors import AuthError, ClientSecretError, TokenFetchError
from apple_ads_platform.auth.client_secret import EphemeralClientSecretProvider
from apple_ads_platform.auth.fixed_client_secret import FixedClientSecretProvider
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher
from apple_ads_platform.auth.token_manager import TokenManager
from apple_ads_platform.auth.api_client import AuthenticatedApiClient

__all__ = [
    "AccessTokenProvider",
    "ClientSecretProvider",
    "AuthError",
    "ClientSecretError",
    "TokenFetchError",
    "EphemeralClientSecretProvider",
    "FixedClientSecretProvider",
    "AccessTokenFetcher",
    "TokenManager",
    "AuthenticatedApiClient",
]
