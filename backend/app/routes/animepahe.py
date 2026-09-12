"""Provider routes that fail closed when no authorized provider is configured."""

from fastapi import APIRouter, Query

from app.core.dependencies import get_video_provider

router = APIRouter(prefix="/api/animepahe", tags=["Video Provider"])


@router.get("/latest")
async def latest(page: int = Query(1, ge=1), limit: int = Query(12, ge=1, le=50)):
    return await get_video_provider().get_latest(page, limit)


@router.post("/cookies")
async def cookies_disabled():
    return await get_video_provider().extract("")


@router.get("/cookies")
async def cookies_disabled_get():
    return await get_video_provider().extract("")


@router.get("/search")
async def search(q: str = Query(..., min_length=1)):
    return await get_video_provider().search(q)


@router.get("/anime/{uuid}/episodes")
async def episodes(uuid: str, page: int = Query(1, ge=1)):
    return await get_video_provider().get_episodes(uuid, page)


@router.get("/episode/{uuid}/{session}/sources")
async def sources(uuid: str, session: str):
    return await get_video_provider().get_sources(uuid, session)


@router.get("/extract")
async def extract(url: str = Query(...)):
    return await get_video_provider().extract(url)


@router.get("/proxy")
async def proxy(url: str = Query(...)):
    return await get_video_provider().proxy(url)
