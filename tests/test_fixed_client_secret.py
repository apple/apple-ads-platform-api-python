# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import pytest

from apple_ads_platform.auth import FixedClientSecretProvider
from apple_ads_platform.auth.errors import ClientSecretError


class TestFixedClientSecretProvider:

    def test_create_secret_returns_provided_value(self):
        provider = FixedClientSecretProvider("my-secret")
        assert provider.create_secret() == "my-secret"

    def test_create_secret_is_idempotent(self):
        provider = FixedClientSecretProvider("my-secret")
        assert provider.create_secret() == provider.create_secret()

    @pytest.mark.parametrize("empty", ["", None])
    def test_empty_secret_rejected(self, empty):
        with pytest.raises(ClientSecretError, match="client_secret must not be empty"):
            FixedClientSecretProvider(empty)
