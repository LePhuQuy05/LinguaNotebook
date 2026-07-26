"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Search, X } from "lucide-react";

interface SearchResult {
  chunk_id: string;
  content: string;
  document_id: string;
  block_type: string;
  language: string;
  difficulty: string;
  score: number;
}

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const token = localStorage.getItem("token");
    const res = await fetch(
      `/api/v1/rag/search?q=${encodeURIComponent(q)}&limit=10`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.ok) {
      const data = await res.json();
      setResults(data.results);
      setShowResults(true);
    }
    setLoading(false);
  }, []);

  return (
    <div ref={ref} className="relative w-full max-w-2xl">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            doSearch(e.target.value);
          }}
          onFocus={() => results.length > 0 && setShowResults(true)}
          placeholder="Search across all your documents..."
          className="w-full rounded-lg border border-border bg-surface py-2.5 pl-10 pr-8 text-sm text-foreground placeholder:text-foreground-subtle focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setResults([]);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border border-border bg-surface shadow-xl">
          {results.map((r) => (
            <div
              key={r.chunk_id}
              className="cursor-pointer border-b border-border p-4 last:border-b-0 transition-colors hover:bg-surface-hover"
            >
              <p className="line-clamp-3 text-sm text-foreground">{r.content}</p>
              <div className="mt-1 flex items-center gap-2 text-xs text-foreground-muted">
                <span>{r.block_type}</span>
                <span>·</span>
                <span>{r.language}</span>
                <span>·</span>
                <span className="text-primary-500">{(r.score * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {loading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
        </div>
      )}
    </div>
  );
}
