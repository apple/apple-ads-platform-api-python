# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
"""Forward-compatibility tests for enum deserialization.

When the server introduces a new enum case the current library version
doesn't know about, deserialization must not fail. These tests verify that
unknown values are mapped to the catch-all UNKNOWN_DEFAULT_OPEN_API enum case
rather than raising.

This test behavior is worth confirming since it has been implemented here
locally (as of writing the Python generator does not support this behavior).
This references specific model classes which is otherwise avoided.
"""
import json

from apple_ads_platform.models.ad import Ad
from apple_ads_platform.models.ad_system_status_reason import AdSystemStatusReason


class TestEnumForwardCompat:

    def test_known_value_maps_to_member(self):
        assert AdSystemStatusReason("PROCESSING") is AdSystemStatusReason.PROCESSING

    def test_unknown_value_maps_to_sentinel(self):
        assert (
            AdSystemStatusReason("BRAND_NEW_REASON_FROM_SERVER")
            is AdSystemStatusReason.UNKNOWN_DEFAULT_OPEN_API
        )

    def test_unknown_in_nested_model_does_not_raise(self):
        ad = Ad.from_dict({
            "id": 1,
            "name": "test",
            "systemStatusReasons": ["PAUSED_BY_USER", "FUTURE_VALUE_NOT_IN_SPEC"],
        })
        assert ad.system_status_reasons == [
            AdSystemStatusReason.PAUSED_BY_USER,
            AdSystemStatusReason.UNKNOWN_DEFAULT_OPEN_API,
        ]

    def test_unknown_via_from_json(self):
        ad = Ad.from_json(json.dumps({
            "id": 1,
            "systemStatusReasons": ["FUTURE_VALUE_NOT_IN_SPEC"],
        }))
        assert ad.system_status_reasons[0] is AdSystemStatusReason.UNKNOWN_DEFAULT_OPEN_API
