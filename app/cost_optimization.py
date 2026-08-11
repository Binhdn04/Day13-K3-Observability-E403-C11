"""Bound model output and cache deterministic mock responses."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


def max_output_tokens() -> int | None:
    """Return the configured output cap; 0 disables the cap for comparison runs."""
    value = int(os.getenv("MAX_OUTPUT_TOKENS", "120"))
    return value if value > 0 else None


def response_cache_enabled() -> bool:
    return os.getenv("RESPONSE_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class CachedResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class ResponseCache:
    def __init__(self) -> None:
        self._items: dict[str, CachedResponse] = {}

    @staticmethod
    def key(prompt: str, model: str, output_cap: int | None) -> str:
        payload = f"{model}\0{output_cap}\0{prompt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, prompt: str, model: str, output_cap: int | None) -> CachedResponse | None:
        if not response_cache_enabled():
            return None
        return self._items.get(self.key(prompt, model, output_cap))

    def put(self, prompt: str, output_cap: int | None, response: CachedResponse) -> None:
        if response_cache_enabled():
            self._items[self.key(prompt, response.model, output_cap)] = response


response_cache = ResponseCache()
