# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from apple_ads_platform.auth.errors import TokenFetchError
from apple_ads_platform.auth.token_fetcher import AccessTokenFetcher
from apple_ads_platform.auth.token_manager import TokenManager


class TestTokenManager:

    def _make_mock_fetcher(
        self, token: str = "mock-token", expires_in: int = 3600
    ) -> MagicMock:
        fetcher = MagicMock(spec=AccessTokenFetcher)
        fetcher.fetch_token.return_value = (token, expires_in)
        return fetcher

    def test_eager_fetch_on_init(self):
        fetcher = self._make_mock_fetcher()
        with TokenManager(fetcher) as tm:
            fetcher.fetch_token.assert_called_once()

    def test_get_token_returns_cached(self):
        fetcher = self._make_mock_fetcher()
        with TokenManager(fetcher) as tm:
            token1 = tm.get_token()
            token2 = tm.get_token()
            assert token1 == "mock-token"
            assert token2 == "mock-token"
            fetcher.fetch_token.assert_called_once()

    def test_refresh_token_fetches_new_token(self):
        fetcher = self._make_mock_fetcher()
        fetcher.fetch_token.side_effect = [
            ("token-1", 3600),
            ("token-2", 3600),
        ]
        with TokenManager(fetcher) as tm:
            assert tm.get_token() == "token-1"
            tm.refresh_token()
            assert tm.get_token() == "token-2"
            assert fetcher.fetch_token.call_count == 2

    def test_get_token_refreshes_when_expired(self):
        fetcher = self._make_mock_fetcher(expires_in=1)
        fetcher.fetch_token.side_effect = [
            ("token-1", 1),
            ("token-2", 3600),
        ]
        with TokenManager(fetcher) as tm:
            assert tm.get_token() == "token-1"
            time.sleep(1.1)
            assert tm.get_token() == "token-2"

    def test_background_refresh_is_scheduled(self):
        fetcher = self._make_mock_fetcher()
        with TokenManager(fetcher) as tm:
            assert tm._timer is not None
            assert tm._timer.is_alive()

    def test_close_cancels_timer(self):
        fetcher = self._make_mock_fetcher()
        tm = TokenManager(fetcher)
        timer = tm._timer
        tm.close()
        timer.join(timeout=1.0)
        assert not timer.is_alive()

    def test_thread_safety(self):
        fetcher = self._make_mock_fetcher(expires_in=0)
        call_count = 0
        original_fetch = fetcher.fetch_token

        def counting_fetch():
            nonlocal call_count
            call_count += 1
            return (f"token-{call_count}", 3600)

        fetcher.fetch_token.side_effect = counting_fetch

        with TokenManager(fetcher) as tm:
            initial_count = call_count
            time.sleep(0.1)

            threads = []
            for _ in range(10):
                t = threading.Thread(target=tm.get_token)
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

            assert call_count <= initial_count + 2

    def test_init_raises_on_fetch_failure(self):
        fetcher = MagicMock(spec=AccessTokenFetcher)
        fetcher.fetch_token.side_effect = TokenFetchError("connection refused")
        with pytest.raises(TokenFetchError):
            TokenManager(fetcher)

    def test_background_refresh_failure_schedules_retry(self):
        fetcher = self._make_mock_fetcher()
        fetcher.fetch_token.side_effect = [
            ("token-1", 3600),
            TokenFetchError("temporary failure"),
            ("token-2", 3600),
        ]
        with TokenManager(fetcher) as tm:
            assert tm.get_token() == "token-1"
            tm._background_refresh()
            assert tm.get_token() == "token-1"
            assert tm._timer is not None
            assert tm._timer.is_alive()
