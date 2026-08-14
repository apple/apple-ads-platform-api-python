# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import time

import jwt
import pytest
from keygen import (
    generate_ec_private_key_pem,
    generate_rsa_private_key_pem,
    public_key_pem_from_private,
)

from apple_ads_platform.auth.client_secret import EphemeralClientSecretProvider
from apple_ads_platform.auth.errors import ClientSecretError

PRIVATE_KEY_PEM = generate_ec_private_key_pem()
PUBLIC_KEY_PEM = public_key_pem_from_private(PRIVATE_KEY_PEM)

CLIENT_ID = "test-client-id"
TEAM_ID = "test-team-id"
KEY_ID = "test-key-id"


class TestEphemeralClientSecretProvider:

    def test_create_secret_returns_valid_jwt(self):
        provider = EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, PRIVATE_KEY_PEM)
        secret = provider.create_secret()

        public_key = PUBLIC_KEY_PEM
        decoded = jwt.decode(
            secret,
            public_key,
            algorithms=["ES256"],
            audience="https://appleid.apple.com",
        )
        assert decoded["iss"] == TEAM_ID
        assert decoded["sub"] == CLIENT_ID
        assert decoded["aud"] == "https://appleid.apple.com"

    def test_header_contains_key_id_and_algorithm(self):
        provider = EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, PRIVATE_KEY_PEM)
        secret = provider.create_secret()

        header = jwt.get_unverified_header(secret)
        assert header["alg"] == "ES256"
        assert header["kid"] == KEY_ID

    def test_expiry_is_180_days(self):
        provider = EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, PRIVATE_KEY_PEM)
        before = int(time.time())
        secret = provider.create_secret()
        after = int(time.time()) + 1

        public_key = PUBLIC_KEY_PEM
        decoded = jwt.decode(
            secret,
            public_key,
            algorithms=["ES256"],
            audience="https://appleid.apple.com",
        )
        expected_expiry = 86400 * 180
        assert decoded["exp"] - decoded["iat"] == expected_expiry
        assert before <= decoded["iat"] <= after

    def test_rejects_empty_private_key_pem(self):
        with pytest.raises(ClientSecretError, match="private_key_pem must not be empty"):
            EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, "")

    def test_rejects_unparseable_pem(self):
        with pytest.raises(ClientSecretError, match="Failed to parse private key"):
            EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, "not a pem")

    def test_rejects_empty_client_id(self):
        with pytest.raises(ClientSecretError, match="client_id must not be empty"):
            EphemeralClientSecretProvider("", TEAM_ID, KEY_ID, PRIVATE_KEY_PEM)

    def test_rejects_empty_team_id(self):
        with pytest.raises(ClientSecretError, match="team_id must not be empty"):
            EphemeralClientSecretProvider(CLIENT_ID, "", KEY_ID, PRIVATE_KEY_PEM)

    def test_rejects_empty_key_id(self):
        with pytest.raises(ClientSecretError, match="key_id must not be empty"):
            EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, "", PRIVATE_KEY_PEM)

    def test_rejects_non_ec_key(self):
        rsa_pem = generate_rsa_private_key_pem()
        with pytest.raises(ClientSecretError, match="Expected an EC private key"):
            EphemeralClientSecretProvider(CLIENT_ID, TEAM_ID, KEY_ID, rsa_pem)
