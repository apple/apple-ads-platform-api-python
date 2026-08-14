# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
class AuthError(Exception):
    """Base exception for auth errors."""


class ClientSecretError(AuthError):
    """Raised when client secret generation fails (bad key, wrong key type, etc.)."""


class TokenFetchError(AuthError):
    """Raised when token fetch from OAuth endpoint fails (HTTP error, bad response, etc.)."""
