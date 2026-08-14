# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import json
from unittest.mock import MagicMock, patch

import pytest
from keygen import generate_ec_private_key_pem, write_pem_to_temp_file

from apple_ads_platform.api.apple_ads_api import AppleAdsApi
from apple_ads_platform.auth.api_client import AuthenticatedApiClient
from apple_ads_platform.builder import AppleAdsClientBuilder, InvalidBuilderConfigurationError
from apple_ads_platform.log_level import LogLevel

PRIVATE_KEY_PEM = generate_ec_private_key_pem()
PRIVATE_KEY_PATH = write_pem_to_temp_file(PRIVATE_KEY_PEM)


def _mock_token_response():
    response = MagicMock()
    response.status = 200
    response.data = json.dumps(
        {"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600}
    ).encode()
    return response


class _StaticTokenProvider:
    def get_token(self) -> str:
        return "custom-token"


class _StaticSecretProvider:
    def create_secret(self) -> str:
        return "static-secret"


class TestDirectInstantiation:

    def test_direct_construction_raises(self):
        with pytest.raises(
            InvalidBuilderConfigurationError,
            match="cannot be instantiated directly",
        ):
            AppleAdsClientBuilder()

    def test_error_points_at_factories(self):
        with pytest.raises(InvalidBuilderConfigurationError, match="from_\\* class methods"):
            AppleAdsClientBuilder()


class TestFromPrivateKey:

    def test_happy_path_returns_builder(self):
        b = AppleAdsClientBuilder.from_private_key(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PEM
        )
        assert isinstance(b, AppleAdsClientBuilder)

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_build_returns_apple_ads_api(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = AppleAdsClientBuilder.from_private_key(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PEM
        ).build()
        assert isinstance(client, AppleAdsApi)
        assert isinstance(client.api_client, AuthenticatedApiClient)

    @pytest.mark.parametrize(
        "args, missing",
        [
            (("", "tid", "kid", PRIVATE_KEY_PEM), "client_id"),
            (("cid", "", "kid", PRIVATE_KEY_PEM), "team_id"),
            (("cid", "tid", "", PRIVATE_KEY_PEM), "key_id"),
            (("cid", "tid", "kid", ""), "private_key"),
        ],
    )
    def test_empty_arg_rejected(self, args, missing):
        with pytest.raises(
            InvalidBuilderConfigurationError, match=f"{missing} must not be empty"
        ):
            AppleAdsClientBuilder.from_private_key(*args)


class TestFromPrivateKeyPath:

    def test_happy_path(self):
        b = AppleAdsClientBuilder.from_private_key_path(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
        )
        assert isinstance(b, AppleAdsClientBuilder)

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_build_returns_apple_ads_api(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = AppleAdsClientBuilder.from_private_key_path(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
        ).build()
        assert isinstance(client, AppleAdsApi)

    def test_empty_path_rejected(self):
        with pytest.raises(InvalidBuilderConfigurationError, match="path must not be empty"):
            AppleAdsClientBuilder.from_private_key_path("cid", "tid", "kid", "")

    def test_unreadable_path_rejected(self):
        with pytest.raises(
            InvalidBuilderConfigurationError, match="Failed to read private key from path"
        ):
            AppleAdsClientBuilder.from_private_key_path(
                "cid", "tid", "kid", "/nonexistent/key.pem"
            )


class TestFromClientSecretProvider:

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_build_returns_apple_ads_api(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = AppleAdsClientBuilder.from_client_secret_provider(
            "test-client", _StaticSecretProvider()
        ).build()
        assert isinstance(client, AppleAdsApi)

    def test_empty_client_id_rejected(self):
        with pytest.raises(
            InvalidBuilderConfigurationError, match="client_id must not be empty"
        ):
            AppleAdsClientBuilder.from_client_secret_provider("", _StaticSecretProvider())

    def test_none_provider_rejected(self):
        with pytest.raises(InvalidBuilderConfigurationError, match="provider must not be None"):
            AppleAdsClientBuilder.from_client_secret_provider("cid", None)


class TestFromAccessTokenProvider:

    def test_build_returns_apple_ads_api(self):
        # No token-fetch http call expected — provider bypasses auth server entirely.
        client = AppleAdsClientBuilder.from_access_token_provider(
            _StaticTokenProvider()
        ).build()
        assert isinstance(client, AppleAdsApi)
        assert isinstance(client.api_client, AuthenticatedApiClient)

    def test_none_provider_rejected(self):
        with pytest.raises(InvalidBuilderConfigurationError, match="provider must not be None"):
            AppleAdsClientBuilder.from_access_token_provider(None)


class TestAccessTokenProviderModeRejections:

    @pytest.mark.parametrize(
        "setter, arg",
        [
            ("auth_base_url", "https://other.example.com"),
            ("auth_timeout", 10.0),
            ("auth_log_level", LogLevel.BASIC),
            ("auth_proxy", "http://proxy.example.com:8080"),
            ("auth_proxy_headers", {"X": "Y"}),
        ],
    )
    def test_auth_setter_rejected(self, setter, arg):
        b = AppleAdsClientBuilder.from_access_token_provider(_StaticTokenProvider())
        with pytest.raises(
            InvalidBuilderConfigurationError,
            match=f"'{setter}' is not applicable when the builder is created via "
            "from_access_token_provider",
        ):
            getattr(b, setter)(arg)

    def test_non_auth_setters_allowed(self):
        # base_url and api_* setters apply regardless of auth mode.
        b = AppleAdsClientBuilder.from_access_token_provider(_StaticTokenProvider())
        b.base_url("https://other-api.example.com").api_timeout(10.0).api_log_level(
            LogLevel.BASIC
        ).api_proxy("http://proxy.example.com:8080")
        client = b.build()
        assert client.api_client.configuration.host == "https://other-api.example.com"


class TestLogLevelValidation:

    def test_auth_log_level_body_forbidden(self):
        b = AppleAdsClientBuilder.from_private_key(
            "cid", "tid", "kid", PRIVATE_KEY_PEM
        )
        with pytest.raises(InvalidBuilderConfigurationError, match="BODY.*forbidden"):
            b.auth_log_level(LogLevel.BODY)

    def test_invalid_api_log_level_raises(self):
        b = AppleAdsClientBuilder.from_private_key(
            "cid", "tid", "kid", PRIVATE_KEY_PEM
        )
        with pytest.raises(InvalidBuilderConfigurationError, match="Invalid api_log_level"):
            b.api_log_level("INVALID")

    def test_invalid_auth_log_level_raises(self):
        b = AppleAdsClientBuilder.from_private_key(
            "cid", "tid", "kid", PRIVATE_KEY_PEM
        )
        with pytest.raises(InvalidBuilderConfigurationError, match="Invalid auth_log_level"):
            b.auth_log_level("DEBUG")


class TestConfigurationFlow:

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_api_timeout_flows_to_configuration(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = (
            AppleAdsClientBuilder.from_private_key_path(
                "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
            )
            .api_timeout(15.0)
            .build()
        )
        assert client.api_client.configuration.request_timeout == 15.0

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_api_proxy_flows_to_configuration(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = (
            AppleAdsClientBuilder.from_private_key_path(
                "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
            )
            .api_proxy("http://proxy.example.com:8080")
            .build()
        )
        assert client.api_client.configuration.proxy == "http://proxy.example.com:8080"

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_api_proxy_headers_flows_to_configuration(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        headers = {"Proxy-Authorization": "Basic dXNlcjpwYXNz"}
        client = (
            AppleAdsClientBuilder.from_private_key_path(
                "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
            )
            .api_proxy("http://proxy.example.com:8080")
            .api_proxy_headers(headers)
            .build()
        )
        assert client.api_client.configuration.proxy_headers == headers

    def test_api_proxy_headers_without_proxy_raises(self):
        with pytest.raises(
            InvalidBuilderConfigurationError, match="api_proxy_headers requires api_proxy"
        ):
            (
                AppleAdsClientBuilder.from_private_key_path(
                    "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
                )
                .api_proxy_headers({"Proxy-Authorization": "Basic dXNlcjpwYXNz"})
                .build()
            )

    @patch("apple_ads_platform.builder.urllib3.ProxyManager")
    def test_auth_proxy_uses_proxy_manager(self, mock_proxy_cls):
        mock_proxy_cls.return_value.request.return_value = _mock_token_response()
        AppleAdsClientBuilder.from_private_key_path(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
        ).auth_proxy("http://proxy.example.com:8080").build()
        mock_proxy_cls.assert_called_once()
        assert mock_proxy_cls.call_args[0][0] == "http://proxy.example.com:8080"

    @patch("apple_ads_platform.builder.urllib3.ProxyManager")
    def test_auth_proxy_headers_passed_to_proxy_manager(self, mock_proxy_cls):
        mock_proxy_cls.return_value.request.return_value = _mock_token_response()
        headers = {"Proxy-Authorization": "Basic dXNlcjpwYXNz"}
        AppleAdsClientBuilder.from_private_key_path(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
        ).auth_proxy("http://proxy.example.com:8080").auth_proxy_headers(headers).build()
        assert mock_proxy_cls.call_args[1]["proxy_headers"] == headers

    def test_auth_proxy_headers_without_proxy_raises(self):
        with pytest.raises(
            InvalidBuilderConfigurationError, match="auth_proxy_headers requires auth_proxy"
        ):
            (
                AppleAdsClientBuilder.from_private_key_path(
                    "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
                )
                .auth_proxy_headers({"Proxy-Authorization": "Basic dXNlcjpwYXNz"})
                .build()
            )


class TestAuthHeaderInjection:

    @patch("apple_ads_platform.builder.urllib3.PoolManager")
    def test_auth_header_injected(self, mock_pool_cls):
        mock_pool_cls.return_value.request.return_value = _mock_token_response()
        client = AppleAdsClientBuilder.from_private_key_path(
            "test-client", "test-team", "test-key", PRIVATE_KEY_PATH
        ).build()

        api_response = MagicMock()
        api_response.status = 200
        api_response.headers = {}
        api_response.data = b'{"data": []}'
        client.api_client.rest_client.request = MagicMock(return_value=api_response)

        client.api_client.call_api("GET", "https://api.ads.apple.com/v1/test")

        call_args = client.api_client.rest_client.request.call_args
        headers = call_args[1].get("headers", {})
        assert headers.get("Authorization") == "Bearer test-token"
