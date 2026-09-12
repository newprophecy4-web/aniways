"""Authorized video-provider interface for Aniways.

A provider must be explicitly configured and authorized by the operator.  The
base deployment intentionally has no video provider configured.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import HTTPException


class VideoProvider(Protocol):
    async def search(self, query: str) -> list[dict[str, Any]]: ...
    async def get_episodes(self, anime_id: str, page: int = 1) -> dict[str, Any]: ...
    async def get_sources(self, anime_id: str, episode_id: str) -> dict[str, Any]: ...


class UnavailableVideoProvider:
    """Fail closed until an approved provider is configured."""

    detail = "No authorized video provider is configured."

    def _unavailable(self) -> None:
        raise HTTPException(status_code=503, detail=self.detail)

    async def search(self, query: str) -> list[dict[str, Any]]:
        self._unavailable()

    async def get_episodes(self, anime_id: str, page: int = 1) -> dict[str, Any]:
        self._unavailable()

    async def get_sources(self, anime_id: str, episode_id: str) -> dict[str, Any]:
        self._unavailable()

    async def get_latest(self, page: int = 1, limit: int = 12) -> dict[str, Any]:
        self._unavailable()

    async def extract(self, url: str) -> dict[str, Any]:
        self._unavailable()

    async def proxy(self, url: str) -> None:
        self._unavailable()
