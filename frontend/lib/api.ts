import type {
  Anime,
  WatchResponse,
  AnimeEpisodesResponse,
  LatestRelease,
  EpisodeInfo,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:4444";

// Re-export types for backward compatibility
export type { Anime, WatchResponse, AnimeEpisodesResponse, LatestRelease, EpisodeInfo };
export type { Episode, VideoSource } from "@/types";

// Retry configuration for API calls
const INITIAL_RETRY_DELAY = 1000; // 1 second
const MAX_RETRY_DELAY = 10000; // 10 seconds

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly providerStatus?: number;

  constructor(message: string, status: number, code?: string, providerStatus?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.providerStatus = providerStatus;
  }
}

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchWithRetry<T>(
  url: string,
  retries = 2,
  delay = INITIAL_RETRY_DELAY
): Promise<T> {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      let payload: { detail?: string; error?: string; provider_status?: number } = {};
      try {
        payload = await res.json();
      } catch {
        // Preserve the HTTP status when the server sends no JSON body.
      }
      throw new ApiError(
        payload.detail || `API request failed (${res.status})`,
        res.status,
        payload.error,
        payload.provider_status,
      );
    }
    return res.json();
  } catch (error) {
    // Check if it's a network error (backend not ready) and we have retries left
    if (retries > 0 && error instanceof TypeError) {
      console.log(`API not ready, retrying in ${delay}ms... (${retries} retries left)`);
      await sleep(delay);
      // Exponential backoff with max delay cap
      const nextDelay = Math.min(delay * 1.5, MAX_RETRY_DELAY);
      return fetchWithRetry<T>(url, retries - 1, nextDelay);
    }
    throw error;
  }
}

async function fetchApi<T>(
  endpoint: string,
  params?: Record<string, string | number>
): Promise<T> {
  const url = new URL(`${API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });
  }

  return fetchWithRetry<T>(url.toString());
}

// API endpoints (MAL Scraper + Animepahe)
export const api = {
  // Search anime
  searchAnime: (q: string, page = 1) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/anime", { q, page }),

  // Get anime details
  getAnime: (id: number) => fetchApi<{ data: Anime }>(`/api/anime/${id}`),
  getAnimeFull: (id: number) => fetchApi<{ data: Anime }>(`/api/anime/${id}/full`),
  
  // Get anime recommendations
  getRecommendations: (id: number, limit = 12) =>
    fetchApi<{ data: { mal_id: number; title: string; title_english?: string; images: Anime["images"]; votes: number }[] }>(`/api/anime/${id}/recommendations`, { limit }),

  // Get anime characters
  getCharacters: (id: number, limit = 12) =>
    fetchApi<{ data: { mal_id: number; name: string; images: { jpg?: { image_url?: string } }; role: string; voice_actor?: { mal_id: number; name: string; images: { jpg?: { image_url?: string } } } | null }[] }>(`/api/anime/${id}/characters`, { limit }),

  // Top anime lists
  getTopAnime: (filter = "airing", page = 1, limit = 24, type?: string) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/top/anime", { filter, page, limit, ...(type && { type }) }),
  
  // Browse anime with filters and sorting
  browseAnime: (params: { status?: string; order_by?: string; sort?: string; page?: number; limit?: number } = {}) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/browse/anime", {
      ...(params.status && { status: params.status }),
      ...(params.order_by && { order_by: params.order_by }),
      ...(params.sort && { sort: params.sort }),
      page: params.page || 1,
      limit: params.limit || 24,
    }),

  // Seasonal anime
  getCurrentSeason: (page = 1, limit = 24) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/seasons/now", { page, limit }),
  getUpcoming: (page = 1, limit = 24) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/seasons/upcoming", { page, limit }),
  getSeason: (year: number, season: string, page = 1, limit = 24) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>(`/api/seasons/${year}/${season}`, { page, limit }),

  // Latest releases from Animepahe
  getLatestReleases: (page = 1, limit = 12) =>
    fetchApi<{ data: LatestRelease[]; total: number; current_page: number; last_page: number }>("/api/animepahe/latest", { page, limit }),

  // Watch (Animepahe sources)
  getWatchSources: (malId: number, episode: number, quality = "1080") =>
    fetchApi<WatchResponse>(`/api/watch/${malId}/${episode}`, { quality }),

  // Get all episodes with sources
  getAllSources: (malId: number) =>
    fetchApi<AnimeEpisodesResponse>(`/api/anime/${malId}/sources`),

  // Get Animepahe info for MAL ID
  getAnimepaheInfo: (malId: number) =>
    fetchApi<{ mal_id: number; title: string; match: { uuid: string; title: string }; total_episodes: number }>(`/api/anime/${malId}/animepahe`),

  // Get all episode titles from MAL
  getEpisodes: (malId: number) =>
    fetchApi<{ mal_id: number; total: number; episodes: EpisodeInfo[] }>(`/api/anime/${malId}/episodes`),

  // Extract video URL
  extractVideo: (kwikUrl: string) =>
    fetchApi<{ embed: string; video: string }>("/api/animepahe/extract", { url: kwikUrl }),

  // Schedule
  getSchedule: (day?: string) =>
    fetchApi<{ data: Anime[]; pagination: { last_visible_page: number; has_next_page: boolean } }>("/api/schedules", day ? { filter: day } : {}),
};
