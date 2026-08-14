# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
from apple_ads_platform.auth.errors import ClientSecretError


class FixedClientSecretProvider:

    def __init__(self, client_secret: str) -> None:
        if not client_secret:
            raise ClientSecretError("client_secret must not be empty")
        self._client_secret = client_secret

    def create_secret(self) -> str:
        return self._client_secret
