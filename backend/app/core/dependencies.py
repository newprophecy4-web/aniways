"""Shared application dependencies."""

import httpx

from app.providers import UnavailableVideoProvider

_client: httpx.AsyncClient | None = None
_video_provider = UnavailableVideoProvider()


def get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialized")
    return _client


def get_video_provider() -> UnavailableVideoProvider:
    return _video_provider


def init_dependencies(client: httpx.AsyncClient) -> None:
    global _client
    _client = client


async def cleanup_dependencies() -> None:
    global _client
    if _client:
        await _client.aclose()
    _client = None
