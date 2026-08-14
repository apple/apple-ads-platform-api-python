# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import json
from unittest.mock import MagicMock

import pytest

from apple_ads_platform.auth.client_secret import EphemeralClientSecretProvider
from apple_ads_platform.auth.errors import TokenFetchError
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher


class TestAccessTokenFetcher:

    def _make_fetcher(self) -> AccessTokenFetcher:
        self._mock_http = MagicMock()
        secret_provider = MagicMock(spec=EphemeralClientSecretProvider)
        secret_provider.create_secret.return_value = "mock-client-secret"
        return AccessTokenFetcher(
            client_id="test-client",
            secret_provider=secret_provider,
            http=self._mock_http,
            auth_base_url="https://appleid.apple.com",
        )

    def _mock_response(self, status: int = 200, body: dict = None) -> MagicMock:
        response = MagicMock()
        response.status = status
        if body is None:
            body = {"access_token": "mock-token", "token_type": "Bearer", "expires_in": 3600}
        response.data = json.dumps(body).encode()
        return response

    def test_fetch_token_returns_token_and_expiry(self):
        fetcher = self._make_fetcher()
        self._mock_http.request.return_value = self._mock_response()

        token, expires_in = fetcher.fetch_token()

        assert token == "mock-token"
        assert expires_in == 3600

    def test_fetch_token_sends_correct_post_body(self):
        fetcher = self._make_fetcher()
        self._mock_http.request.return_value = self._mock_response()

        fetcher.fetch_token()

        self._mock_http.request.assert_called_once()
        call_args = self._mock_http.request.call_args
        assert call_args[0] == ("POST", "https://appleid.apple.com/auth/oauth2/token")
        body = call_args[1]["body"]
        assert "grant_type=client_credentials" in body
        assert "scope=searchadsorg" in body
        assert "client_id=test-client" in body
        assert "client_secret=mock-client-secret" in body
        assert call_args[1]["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    def test_raises_on_non_200_status(self):
        fetcher = self._make_fetcher()
        response = self._mock_response(status=401)
        response.data = b"Unauthorized"
        self._mock_http.request.return_value = response

        with pytest.raises(TokenFetchError, match="status 401"):
            fetcher.fetch_token()

    def test_raises_on_malformed_json(self):
        fetcher = self._make_fetcher()
        response = MagicMock()
        response.status = 200
        response.data = b"not json"
        self._mock_http.request.return_value = response

        with pytest.raises(TokenFetchError, match="Failed to parse"):
            fetcher.fetch_token()

    def test_raises_on_missing_access_token(self):
        fetcher = self._make_fetcher()
        self._mock_http.request.return_value = self._mock_response(body={"expires_in": 3600})

        with pytest.raises(TokenFetchError, match="missing required fields"):
            fetcher.fetch_token()
