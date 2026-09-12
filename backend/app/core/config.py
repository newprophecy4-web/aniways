"""Application configuration with explicit environment-based provider settings."""

import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache

_env = os.getenv
_env_bool = lambda key, default=False: _env(key, str(default)).lower() in ("true", "1", "yes")
_env_int = lambda key, default=0: int(_env(key, str(default)) or default)


@dataclass(frozen=True, slots=True)
class Settings:
    DEBUG: bool = field(default_factory=lambda: _env_bool("DEBUG"))
    HOST: str = field(default_factory=lambda: _env("HOST", "0.0.0.0"))
    PORT: int = field(default_factory=lambda: _env_int("PORT", 4444))
    API_TITLE: str = field(default_factory=lambda: _env("API_TITLE", "Aniways API"))
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "Anime catalog API with an explicitly authorized video-provider interface"
    JIKAN_BASE_URL: str = field(default_factory=lambda: _env("JIKAN_BASE_URL", "https://api.jikan.moe/v4"))
    VIDEO_PROVIDER: str = field(default_factory=lambda: _env("VIDEO_PROVIDER", "none"))
    VIDEO_API_URL: str = field(default_factory=lambda: _env("VIDEO_API_URL", ""))
    VIDEO_API_KEY: str = field(default_factory=lambda: _env("VIDEO_API_KEY", ""))
    JIKAN_RATE_LIMIT_DELAY: float = 0.4
    JIKAN_MAX_RETRIES: int = 3
    CACHE_TTL_SHORT: int = 300
    CACHE_TTL_LONG: int = 3600
    HTTP_TIMEOUT: float = 30.0
    DATA_DIR: str = field(default_factory=lambda: _env("DATA_DIR", "backend"))
    SECRET_KEY: str = field(default_factory=lambda: _env("SECRET_KEY", secrets.token_urlsafe(32)))
    USER_AGENT: str = field(default_factory=lambda: _env("USER_AGENT", "Aniways/2.0 (+authorized-provider-integration)"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
