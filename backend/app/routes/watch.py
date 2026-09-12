"""Watch routes backed only by an explicitly authorized video provider."""

from fastapi import APIRouter, Query

from app.core.dependencies import get_video_provider

router = APIRouter(prefix="/api", tags=["Watch"])


@router.get("/watch/{mal_id}/{episode}")
async def watch(mal_id: int, episode: int, quality: str = Query("1080")):
    return await get_video_provider().get_sources(str(mal_id), str(episode))


@router.get("/anime/{mal_id}/sources")
async def all_sources(mal_id: int):
    return await get_video_provider().get_sources(str(mal_id), "all")


@router.get("/anime/{mal_id}/animepahe")
async def animepahe_info(mal_id: int):
    return await get_video_provider().search(str(mal_id))


@router.get("/anime/{mal_id}/episodes")
async def get_episodes(mal_id: int):
    return await get_video_provider().get_episodes(str(mal_id))
