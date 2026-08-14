# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import json
import logging
from unittest.mock import MagicMock, patch

from apple_ads_platform.auth.api_client import AuthenticatedApiClient
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher
from apple_ads_platform.auth.client_secret import EphemeralClientSecretProvider
from apple_ads_platform.configuration import Configuration
from apple_ads_platform.log_level import LogLevel


class TestApiClientLogging:

    def _make_client(self, log_level):
        class StaticTokenProvider:
            def get_token(self) -> str:
                return "test-token"

        config = Configuration(host="https://api.ads.apple.com/v1")
        return AuthenticatedApiClient(StaticTokenProvider(), config, log_level=log_level)

    def test_basic_logs_method_and_url(self, caplog):
        client = self._make_client(LogLevel.BASIC)

        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.data = b'{"ok": true}'
        client.rest_client.request = MagicMock(return_value=response)

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.api"):
            client.call_api("GET", "https://api.ads.apple.com/v1/test")

        assert any("-> GET https://api.ads.apple.com/v1/test" in r.message for r in caplog.records)
        assert any("<- 200 GET" in r.message for r in caplog.records)
        assert not any("Headers:" in r.message for r in caplog.records)
        assert not any("Body:" in r.message for r in caplog.records)

    def test_headers_logs_with_redaction(self, caplog):
        client = self._make_client(LogLevel.HEADERS)

        response = MagicMock()
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.data = b'{"ok": true}'
        client.rest_client.request = MagicMock(return_value=response)

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.api"):
            client.call_api("GET", "https://api.ads.apple.com/v1/test")

        header_logs = [r.message for r in caplog.records if "Headers:" in r.message]
        assert len(header_logs) >= 1
        request_header_log = header_logs[0]
        assert "[REDACTED]" in request_header_log
        assert "test-token" not in request_header_log

    def test_no_logging_when_disabled(self, caplog):
        client = self._make_client(None)

        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.data = b'{"ok": true}'
        client.rest_client.request = MagicMock(return_value=response)

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.api"):
            client.call_api("GET", "https://api.ads.apple.com/v1/test")

        assert len(caplog.records) == 0

    def test_body_logs_request_and_response_body(self, caplog):
        client = self._make_client(LogLevel.BODY)

        response = MagicMock()
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.read.return_value = b'{"campaigns": []}'
        client.rest_client.request = MagicMock(return_value=response)

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.api"):
            client.call_api("POST", "https://api.ads.apple.com/v1/campaigns/query",
                           body={"filter": "active"})

        messages = [r.message for r in caplog.records]
        assert any("Body: {'filter': 'active'}" in m for m in messages)
        assert any('Body: {"campaigns": []}' in m for m in messages)
        assert any("Headers:" in m for m in messages)
        assert any("[REDACTED]" in m for m in messages)


class TestTokenFetcherLogging:

    def test_basic_logs_request_and_response(self, caplog):
        mock_http = MagicMock()
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.data = json.dumps(
            {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}
        ).encode()
        mock_http.request.return_value = response

        secret_provider = MagicMock(spec=EphemeralClientSecretProvider)
        secret_provider.create_secret.return_value = "mock-secret"

        fetcher = AccessTokenFetcher(
            client_id="test",
            secret_provider=secret_provider,
            http=mock_http,
            log_level=LogLevel.BASIC,
        )

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.auth"):
            fetcher.fetch_token()

        assert any("-> POST" in r.message for r in caplog.records)
        assert any("<- 200 POST" in r.message for r in caplog.records)

    def test_no_logging_when_disabled(self, caplog):
        mock_http = MagicMock()
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.data = json.dumps(
            {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}
        ).encode()
        mock_http.request.return_value = response

        secret_provider = MagicMock(spec=EphemeralClientSecretProvider)
        secret_provider.create_secret.return_value = "mock-secret"

        fetcher = AccessTokenFetcher(
            client_id="test",
            secret_provider=secret_provider,
            http=mock_http,
        )

        with caplog.at_level(logging.INFO, logger="apple_ads_platform.auth"):
            fetcher.fetch_token()

        assert len(caplog.records) == 0
