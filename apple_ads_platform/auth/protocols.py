# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClientSecretProvider(Protocol):
    def create_secret(self) -> str: ...


@runtime_checkable
class AccessTokenProvider(Protocol):
    def get_token(self) -> str: ...
