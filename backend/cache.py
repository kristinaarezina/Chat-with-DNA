"""Simple in-memory cache to avoid redundant API calls during a session."""

_store: dict[str, dict] = {}


def get(key: str) -> dict | None:
    return _store.get(key)


def set(key: str, value: dict) -> None:
    _store[key] = value
