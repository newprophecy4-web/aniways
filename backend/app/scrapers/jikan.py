"""
Jikan API Client
================

Wrapper for Jikan API (MyAnimeList data) with rate limiting and caching.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.dependencies import get_client
from app.utils import cache

logger = logging.getLogger(__name__)

# Rate limiting state
_last_request = 0.0
_rate_lock = asyncio.Lock()


class MetadataProviderError(Exception):
    """A safe, user-facing failure from the anime metadata provider."""

    def __init__(self, message: str, status_code: int, provider_status: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider_status = provider_status


# =============================================================================
# Core API
# =============================================================================


async def _request(endpoint: str, params: dict | None = None) -> dict | None:
    """Make rate-limited request to Jikan API with retries."""
    global _last_request

    for attempt in range(settings.JIKAN_MAX_RETRIES):
        # Rate limiting
        async with _rate_lock:
            elapsed = time.time() - _last_request
            if elapsed < settings.JIKAN_RATE_LIMIT_DELAY:
                await asyncio.sleep(settings.JIKAN_RATE_LIMIT_DELAY - elapsed)
            _last_request = time.time()

        try:
            resp = await get_client().get(
                f"{settings.JIKAN_BASE_URL}{endpoint}",
                params=params,
                follow_redirects=True,
            )

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 1))
                logger.warning("Rate limited, waiting %ds", wait)
                await asyncio.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        except httpx.TimeoutException as e:
            logger.warning("Jikan timeout (attempt %d): %s", attempt + 1, e)
            if attempt == settings.JIKAN_MAX_RETRIES - 1:
                raise MetadataProviderError("Anime metadata provider timed out", 504) from e
            await asyncio.sleep(0.5 * (2 ** attempt))
        except httpx.HTTPStatusError as e:
            provider_status = e.response.status_code
            logger.warning("Jikan HTTP error (attempt %d): %s", attempt + 1, e)
            if provider_status == 429:
                raise MetadataProviderError("Anime metadata provider rate limited the request", 429, provider_status) from e
            if provider_status < 500:
                raise MetadataProviderError("Anime metadata provider rejected the request", 502, provider_status) from e
            if attempt == settings.JIKAN_MAX_RETRIES - 1:
                status_code = 504 if provider_status == 504 else 503
                raise MetadataProviderError("Anime metadata provider is unavailable", status_code, provider_status) from e
            await asyncio.sleep(0.5 * (2 ** attempt))
        except httpx.RequestError as e:
            logger.warning("Jikan connection error (attempt %d): %s", attempt + 1, e)
            if attempt == settings.JIKAN_MAX_RETRIES - 1:
                raise MetadataProviderError("Unable to reach anime metadata provider", 503) from e
            await asyncio.sleep(0.5 * (2 ** attempt))
        except Exception as e:
            logger.warning("Jikan error (attempt %d): %s", attempt + 1, e)
            if attempt < settings.JIKAN_MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                raise MetadataProviderError("Anime metadata provider returned an invalid response", 502) from e

    raise MetadataProviderError("Anime metadata provider is unavailable", 503)


def _normalize(anime: dict) -> dict:
    """Normalize Jikan anime response to consistent format."""
    img = anime.get("images", {})
    jpg, webp = img.get("jpg", {}), img.get("webp", {})

    return {
        "mal_id": anime.get("mal_id"),
        "url": anime.get("url"),
        "title": anime.get("title"),
        "title_english": anime.get("title_english"),
        "title_japanese": anime.get("title_japanese"),
        "title_synonyms": anime.get("title_synonyms", []),
        "images": {
            "jpg": {k: jpg.get(k) for k in ("image_url", "small_image_url", "large_image_url")},
            "webp": {k: webp.get(k) for k in ("image_url", "small_image_url", "large_image_url")},
        },
        "type": anime.get("type"),
        "source": anime.get("source"),
        "episodes": anime.get("episodes"),
        "status": anime.get("status"),
        "airing": anime.get("airing"),
        "aired": anime.get("aired"),
        "duration": anime.get("duration"),
        "rating": anime.get("rating"),
        "score": anime.get("score"),
        "scored_by": anime.get("scored_by"),
        "rank": anime.get("rank"),
        "popularity": anime.get("popularity"),
        "members": anime.get("members"),
        "favorites": anime.get("favorites"),
        "synopsis": anime.get("synopsis"),
        "background": anime.get("background"),
        "season": anime.get("season"),
        "year": anime.get("year"),
        "broadcast": anime.get("broadcast"),
        "producers": anime.get("producers", []),
        "licensors": anime.get("licensors", []),
        "studios": anime.get("studios", []),
        "genres": anime.get("genres", []),
        "themes": anime.get("themes", []),
        "demographics": anime.get("demographics", []),
        "relations": anime.get("relations", []),
        "streaming": anime.get("streaming", []),
    }


def _empty_page() -> dict:
    """Return empty paginated response."""
    return {"data": [], "pagination": {"last_visible_page": 1, "has_next_page": False}}


# =============================================================================
# Public API
# =============================================================================


async def scrape_top_anime(
    filter_type: str = "airing",
    limit: int = 10,
    anime_type: str | None = None,
    page: int = 1,
) -> dict:
    """Get top anime by filter (airing, upcoming, bypopularity, favorite)."""
    key = f"top:{filter_type}:{anime_type}:{limit}:{page}"
    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    params = {"limit": min(limit, 25), "page": page}

    if filter_type in ("airing", "upcoming", "bypopularity", "favorite"):
        params["filter"] = filter_type

    if anime_type and anime_type.lower() in ("tv", "movie", "ova", "special", "ona", "music"):
        params["type"] = anime_type.lower()

    result = await _request("/top/anime", params)
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    response = {
        "data": [_normalize(a) for a in result["data"][:limit]],
        "pagination": {
            "last_visible_page": result.get("pagination", {}).get("last_visible_page", 1),
            "has_next_page": result.get("pagination", {}).get("has_next_page", False),
        },
    }
    cache.set(key, response)
    return response


async def scrape_anime_details(mal_id: int) -> dict | None:
    """Get full anime details by MAL ID."""
    key = f"anime:{mal_id}"
    if cached := cache.get(key, settings.CACHE_TTL_LONG):
        return cached

    result = await _request(f"/anime/{mal_id}/full")
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    anime = _normalize(result["data"])
    cache.set(key, anime)
    return anime


async def browse_anime(
    status: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
    page: int = 1,
    limit: int = 25,
) -> dict:
    """Browse anime with filters and sorting."""
    key = f"browse:{status}:{order_by}:{sort}:{page}:{limit}"
    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    params = {"page": page, "limit": min(limit, 25), "sfw": "false"}

    if status and status.lower() in ("airing", "complete", "upcoming"):
        params["status"] = status.lower()

    if order_by and order_by.lower() in ("score", "popularity", "start_date", "rank", "members"):
        params["order_by"] = order_by.lower()
        params["sort"] = "asc" if sort == "asc" else "desc"

    result = await _request("/anime", params)
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    response = {
        "data": [_normalize(a) for a in result["data"]],
        "pagination": {
            "last_visible_page": result.get("pagination", {}).get("last_visible_page", 1),
            "has_next_page": result.get("pagination", {}).get("has_next_page", False),
        },
    }
    cache.set(key, response)
    return response


async def search_anime(query: str, page: int = 1, limit: int = 25) -> tuple[list[dict], int]:
    """Search anime by query."""
    key = f"search:{query}:{page}:{limit}"
    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    result = await _request("/anime", {"q": query, "page": page, "limit": min(limit, 25), "sfw": "false"})
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    response = (
        [_normalize(a) for a in result["data"]],
        result.get("pagination", {}).get("last_visible_page", 1),
    )
    cache.set(key, response)
    return response


async def scrape_seasonal_anime(
    year: int | None = None,
    season: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Get seasonal anime (current if no year/season specified)."""
    endpoint = f"/seasons/{year}/{season}" if year and season else "/seasons/now"
    key = f"seasonal:{year or 'now'}:{season or ''}:{limit}"

    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    result = await _request(endpoint, {"limit": min(limit, 25)})
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    anime_list = [_normalize(a) for a in result["data"][:limit]]
    cache.set(key, anime_list)
    return anime_list


async def scrape_upcoming_anime(limit: int = 25) -> list[dict]:
    """Get upcoming anime."""
    key = f"upcoming:{limit}"
    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    result = await _request("/seasons/upcoming", {"limit": min(limit, 25)})
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    anime_list = [_normalize(a) for a in result["data"][:limit]]
    cache.set(key, anime_list)
    return anime_list


async def scrape_schedule(day: str | None = None, page: int = 1) -> list[dict]:
    """Get weekly broadcast schedule."""
    key = f"schedule:{day or 'all'}:{page}"
    if cached := cache.get(key, settings.CACHE_TTL_SHORT):
        return cached

    params = {"page": page, "sfw": "true"}
    if day:
        params["filter"] = day

    result = await _request("/schedules", params)
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    anime_list = [_normalize(a) for a in result["data"]]
    cache.set(key, anime_list)
    return anime_list


async def scrape_episode(mal_id: int, episode_num: int) -> dict | None:
    """Get specific episode info."""
    key = f"episode:{mal_id}:{episode_num}"
    if cached := cache.get(key, settings.CACHE_TTL_LONG):
        return cached

    result = await _request(f"/anime/{mal_id}/episodes/{episode_num}")
    if not result or "data" not in result:
        return None

    ep = result["data"]
    episode = {
        "mal_id": ep.get("mal_id"),
        "episode": episode_num,
        "title": ep.get("title"),
        "title_japanese": ep.get("title_japanese"),
        "title_romanji": ep.get("title_romanji"),
        "aired": ep.get("aired"),
        "filler": ep.get("filler", False),
        "recap": ep.get("recap", False),
    }
    cache.set(key, episode)
    return episode


async def scrape_all_episodes(mal_id: int) -> list[dict]:
    """Get all episodes for anime."""
    key = f"episodes:{mal_id}"
    if cached := cache.get(key, settings.CACHE_TTL_LONG):
        return cached

    episodes = []
    for page in range(1, 11):  # Max 10 pages
        result = await _request(f"/anime/{mal_id}/episodes", {"page": page})
        if not result or not result.get("data"):
            break

        for ep in result["data"]:
            episodes.append({
                "mal_id": ep.get("mal_id"),
                "episode": ep.get("mal_id"),
                "title": ep.get("title"),
                "title_japanese": ep.get("title_japanese"),
                "title_romanji": ep.get("title_romanji"),
                "aired": ep.get("aired"),
                "filler": ep.get("filler", False),
                "recap": ep.get("recap", False),
            })

        if not result.get("pagination", {}).get("has_next_page"):
            break

    cache.set(key, episodes)
    return episodes


async def scrape_recommendations(mal_id: int, limit: int = 12) -> list[dict]:
    """Get anime recommendations."""
    key = f"recommendations:{mal_id}:{limit}"
    if cached := cache.get(key, settings.CACHE_TTL_LONG):
        return cached

    result = await _request(f"/anime/{mal_id}/recommendations")
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    recs = [
        {
            "mal_id": (e := rec.get("entry", {})).get("mal_id"),
            "title": e.get("title"),
            "title_english": e.get("title_english"),
            "images": e.get("images", {}),
            "votes": rec.get("votes", 0),
        }
        for rec in result["data"][:limit]
        if rec.get("entry")
    ]
    cache.set(key, recs)
    return recs


async def scrape_characters(mal_id: int, limit: int = 12) -> list[dict]:
    """Get anime characters with voice actors."""
    key = f"characters:{mal_id}:{limit}"
    if cached := cache.get(key, settings.CACHE_TTL_LONG):
        return cached

    result = await _request(f"/anime/{mal_id}/characters")
    if not result or "data" not in result:
        raise MetadataProviderError("Anime metadata provider returned an invalid response", 502)

    characters = []
    for char in result["data"][:limit]:
        character = char.get("character", {})

        # Find Japanese VA
        jp_va = next(
            (
                {"mal_id": va["person"]["mal_id"], "name": va["person"]["name"], "images": va["person"].get("images", {})}
                for va in char.get("voice_actors", [])
                if va.get("language") == "Japanese"
            ),
            None,
        )

        characters.append({
            "mal_id": character.get("mal_id"),
            "name": character.get("name"),
            "images": character.get("images", {}),
            "role": char.get("role"),
            "voice_actor": jp_va,
        })

    cache.set(key, characters)
    return characters
