# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from apple_ads_platform.auth.errors import ClientSecretError

_AUDIENCE = "https://appleid.apple.com"
_EXPIRY_SECONDS = 86400 * 180


class EphemeralClientSecretProvider:

    def __init__(
        self,
        client_id: str,
        team_id: str,
        key_id: str,
        private_key_pem: str,
    ) -> None:
        if not client_id:
            raise ClientSecretError("client_id must not be empty")
        if not team_id:
            raise ClientSecretError("team_id must not be empty")
        if not key_id:
            raise ClientSecretError("key_id must not be empty")
        if not private_key_pem:
            raise ClientSecretError("private_key_pem must not be empty")

        self._client_id = client_id
        self._team_id = team_id
        self._key_id = key_id

        try:
            key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        except Exception as e:
            raise ClientSecretError(f"Failed to parse private key: {e}") from e

        if not isinstance(key, EllipticCurvePrivateKey):
            raise ClientSecretError(
                f"Expected an EC private key but got {type(key).__name__}"
            )

        self._private_key = key

    def create_secret(self) -> str:
        now = time.time()
        claims = {
            "iss": self._team_id,
            "sub": self._client_id,
            "aud": _AUDIENCE,
            "iat": int(now),
            "exp": int(now + _EXPIRY_SECONDS),
        }
        try:
            return jwt.encode(
                claims,
                self._private_key,
                algorithm="ES256",
                headers={"kid": self._key_id},
            )
        except Exception as e:
            raise ClientSecretError(f"Failed to sign client secret JWT: {e}") from e
