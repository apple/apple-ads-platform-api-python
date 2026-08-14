# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import re
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

from apple_ads_platform.auth.api_client import (
    AuthenticatedApiClient,
    _resolve_version,
    _USER_AGENT,
)
from apple_ads_platform.configuration import Configuration


class TestUserAgent:

    def _make_client(self):
        class StaticTokenProvider:
            def get_token(self) -> str:
                return "test-token"

        config = Configuration(host="https://api.ads.apple.com/v1")
        return AuthenticatedApiClient(StaticTokenProvider(), config)

    def test_user_agent_header_set_on_request(self):
        client = self._make_client()

        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.data = b'{"ok": true}'
        client.rest_client.request = MagicMock(return_value=response)

        client.call_api("GET", "https://api.ads.apple.com/v1/test")

        _, kwargs = client.rest_client.request.call_args
        headers = kwargs.get("headers", {})
        assert headers["User-Agent"] == _USER_AGENT

    def test_user_agent_format(self):
        assert re.match(r"^apple-ads-python-\d+\.\d+\.\d+", _USER_AGENT)

    def test_resolve_version_from_metadata(self):
        version = _resolve_version()
        assert version and len(version) > 0

    def test_resolve_version_fallback_when_not_installed(self):
        with patch(
            "apple_ads_platform.auth.api_client.version",
            side_effect=PackageNotFoundError("apple-ads-platform"),
        ):
            from apple_ads_platform import __version__

            result = _resolve_version()
            assert result == __version__
