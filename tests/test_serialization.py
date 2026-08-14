# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
"""Tests for `ApiClient's serialization` behavior.

This file covers serialization output produced by the generated `ApiClient`.

"""
import datetime as _dt

import pytest

from apple_ads_platform.api_client import ApiClient


@pytest.fixture
def client():
    return ApiClient()


class TestSerialization:

    def test_naive_datetime_emits_millisecond_precision(self, client):
        obj = _dt.datetime(2026, 5, 1, 12, 30, 45, 123_000)
        assert client.sanitize_for_serialization(obj) == "2026-05-01T12:30:45.123"

    def test_naive_datetime_with_zero_microseconds_emits_three_zeros(self, client):
        obj = _dt.datetime(2026, 5, 1, 12, 30, 45)
        assert client.sanitize_for_serialization(obj) == "2026-05-01T12:30:45.000"

    def test_microsecond_precision_truncated_to_milliseconds(self, client):
        obj = _dt.datetime(2026, 5, 1, 12, 30, 45, 123_456)
        assert client.sanitize_for_serialization(obj) == "2026-05-01T12:30:45.123"

    def test_utc_aware_datetime_strips_tz(self, client):
        obj = _dt.datetime(2026, 5, 1, 12, 30, 45, 123_000, tzinfo=_dt.timezone.utc)
        assert client.sanitize_for_serialization(obj) == "2026-05-01T12:30:45.123"

    def test_non_utc_aware_datetime_coerced_to_utc(self, client):
        pdt = _dt.timezone(_dt.timedelta(hours=-7))
        obj = _dt.datetime(2026, 5, 1, 5, 30, 45, 123_000, tzinfo=pdt)
        assert client.sanitize_for_serialization(obj) == "2026-05-01T12:30:45.123"

    def test_date_emits_iso_format(self, client):
        obj = _dt.date(2026, 5, 1)
        assert client.sanitize_for_serialization(obj) == "2026-05-01"

    def test_nested_datetime_in_dict(self, client):
        obj = {"createdAt": _dt.datetime(2026, 5, 1, 12, 30, 45, 123_000)}
        result = client.sanitize_for_serialization(obj)
        assert result == {"createdAt": "2026-05-01T12:30:45.123"}

    def test_datetime_in_list(self, client):
        obj = [_dt.datetime(2026, 5, 1, 12, 30, 45, tzinfo=_dt.timezone.utc)]
        assert client.sanitize_for_serialization(obj) == ["2026-05-01T12:30:45.000"]

    def test_non_datetime_passes_through(self, client):
        assert client.sanitize_for_serialization("hello") == "hello"
        assert client.sanitize_for_serialization(42) == 42
        assert client.sanitize_for_serialization(None) is None