# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
"""Generates throwaway keys as PEM strings for tests.

Keys are generated fresh on each call so that no key material lives in the
repository (which would otherwise trip credential-scanning tools). The emitted
PEM formats match the output of the corresponding OpenSSL commands:

* :func:`generate_ec_private_key_pem` -- SEC1 ``EC PRIVATE KEY``, equivalent to
  ``openssl ecparam -genkey -name prime256v1 -noout``
* :func:`generate_rsa_private_key_pem` -- PKCS#1 ``RSA PRIVATE KEY``, equivalent
  to ``openssl genrsa 2048``
"""
import atexit
import os
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

_RSA_KEY_SIZE = 2048


def generate_ec_private_key_pem() -> str:
    """Return a fresh P-256 (prime256v1 / secp256r1) EC private key in SEC1 PEM
    form. This is the key type expected by ``EphemeralClientSecretProvider`` for
    ES256 signing."""
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode("utf-8")


def public_key_pem_from_private(private_key_pem: str) -> str:
    """Return the ``PUBLIC KEY`` PEM matching the given private key PEM, for
    verifying signatures produced with that private key."""
    key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def generate_rsa_private_key_pem() -> str:
    """Return a fresh 2048-bit RSA private key in PKCS#1 PEM form. Used to
    exercise the negative path where a non-EC key must be rejected."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=_RSA_KEY_SIZE)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode("utf-8")


def write_pem_to_temp_file(pem: str) -> str:
    """Write ``pem`` to a temporary file and return its path. The file is
    removed on interpreter exit so no key material is left on disk."""
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as f:
        f.write(pem)

    def _cleanup() -> None:
        if os.path.exists(path):
            os.remove(path)

    atexit.register(_cleanup)
    return path
