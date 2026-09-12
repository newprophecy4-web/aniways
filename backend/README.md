# Aniways Backend

Aniways Backend is a FastAPI service for anime catalog metadata, search, details, schedules, authentication, and SQLite-backed user lists.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-4444}
```

The service exposes `/health` and interactive API documentation at `/docs`.

## Authorized video provider

Video playback is isolated behind `app.providers.VideoProvider`. The default deployment uses `UnavailableVideoProvider` and returns HTTP 503 with:

```json
{"detail":"No authorized video provider is configured."}
```

An operator may add an explicitly authorized provider adapter through environment-based configuration. Provider URLs, credentials, cookies, signed media URLs, and access-control workarounds must never be hardcoded.

The project does not bypass CAPTCHA, DDoS protection, Cloudflare, anti-bot controls, Referer or Origin protection, IP restrictions, rate limits, authentication, or DRM. It does not proxy or rewrite third-party playlists.

## Environment variables

- `HOST` (default `0.0.0.0`)
- `PORT` (default `4444`)
- `DATA_DIR` (default `backend`)
- `SECRET_KEY` (set a production value)
- `VIDEO_PROVIDER` (default `none`)
- `VIDEO_API_URL` (optional, for an approved provider adapter)
- `VIDEO_API_KEY` (optional runtime secret; never commit it)
- `JIKAN_BASE_URL` (default `https://api.jikan.moe/v4`)
- `CORS_ORIGINS` (comma-separated browser origins; required for production frontend access)

## Main routes

Catalog routes use Jikan/MyAnimeList metadata, including search, details, top anime, seasons, schedules, recommendations, and characters. Authentication and SQLite-backed anime lists remain enabled. Playback-related routes remain present for frontend compatibility but fail closed with HTTP 503 until an authorized provider is configured.

Metadata-provider failures return explicit 502/503/504 responses rather than successful empty catalog results. SQLite stores users and personal lists only. On Render, the SQLite file is ephemeral unless the service is attached to persistent storage, so accounts and lists can be lost when the instance is replaced.
