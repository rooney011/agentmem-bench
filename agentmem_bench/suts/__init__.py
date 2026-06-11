"""SUT adapter registry. Real systems register here as they're implemented."""

from __future__ import annotations

from ..adapter import SUTAdapter
from .fake import FakeSUT

# name -> zero-arg factory. Keep factories lazy so importing this module doesn't
# require a real system's optional deps until that SUT is actually selected.
REGISTRY: dict[str, type[SUTAdapter]] = {
    "fake": FakeSUT,
}


def make(name: str) -> SUTAdapter:
    if name not in REGISTRY:
        raise KeyError(f"unknown SUT '{name}'. Known: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[name]()


def available() -> list[str]:
    return sorted(REGISTRY)
