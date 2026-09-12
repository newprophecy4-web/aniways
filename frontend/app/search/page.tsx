"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { api, ApiError, type Anime } from "@/lib/api";
import { AnimeGrid, AnimeGridSkeleton } from "@/components/anime-grid";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [results, setResults] = useState<Anime[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState(query);
  const [page, setPage] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = query ? `Search: ${query} - Aniways` : "Search - Aniways";
  }, [query]);

  useEffect(() => {
    if (query) {
      setSearchQuery(query);
      setPage(1);
      performSearch(query, 1);
    }
  }, [query]);

  async function performSearch(q: string, pageNum: number) {
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.searchAnime(q, pageNum);
      setResults(res.data || []);
      setHasNextPage(res.pagination?.has_next_page || false);
      setTotalPages(res.pagination?.last_visible_page || 1);
    } catch (error) {
      console.error("Search failed:", error);
      setResults([]);
      if (error instanceof ApiError && error.status >= 502 && error.status <= 504) {
        setError("Anime metadata is temporarily unavailable. Please try again shortly.");
      } else if (error instanceof ApiError && error.status === 429) {
        setError("Too many requests. Please wait a moment and try again.");
      } else {
        setError("The backend could not be reached. Please try again shortly.");
      }
    } finally {
      setLoading(false);
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      window.history.pushState(
        {},
        "",
        `/search?q=${encodeURIComponent(searchQuery.trim())}`,
      );
      setPage(1);
      performSearch(searchQuery.trim(), 1);
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
    performSearch(query, newPage);
  };

  return (
    <div className="space-y-8 mt-10">
      {loading ? (
        <AnimeGridSkeleton count={24} title={`Searching for "${query}"...`} />
      ) : results.length > 0 ? (
        <>
          <AnimeGrid anime={results} title={`Results for "${query}"`} />

          {/* Pagination */}
          {(hasNextPage || page > 1) && (
            <div className="flex items-center justify-center gap-4 pt-4">
              <Button
                variant="outline"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="gap-2"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => handlePageChange(page + 1)}
                disabled={!hasNextPage}
                className="gap-2"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-destructive text-lg">{error}</p>
        </div>
      ) : query ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground text-lg">
            No results found for &quot;{query}&quot;
          </p>
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground text-lg">
            Enter a search term to find anime
          </p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<AnimeGridSkeleton count={24} title="Loading..." />}>
      <SearchContent />
    </Suspense>
  );
}
