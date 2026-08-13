"use client";

import { useEffect, useState } from "react";

interface EmbedProgressProps {
  documentId: string;
  onComplete?: () => void;
}

interface ProgressData {
  status: string;
  current_chunks: number;
  total_chunks: number;
  elapsed_sec: number;
  error?: string;
}

/**
 * Live progress for the RAG indexing phase (chunk → embed → Qdrant).
 * Mirrors ParseProgress's poll loop, but reads the embed progress key and
 * has no cancel button — indexing is cheap to restart, parse is not.
 */
export function EmbedProgress({ documentId, onComplete }: EmbedProgressProps) {
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    let active = true;

    const poll = async () => {
      try {
        const res = await fetch(
          `/api/v1/documents/${documentId}/embed/progress/poll?token=${encodeURIComponent(token || "")}`,
        );
        if (!res.ok || !active) return;
        const data: ProgressData = await res.json();
        setProgress(data);

        if (data.status === "embedded" || data.status === "embed_failed") {
          onComplete?.();
          return;
        }
        if (data.status === "failed") return;
      } catch {
        // Retry on next poll
      }

      if (active) setTimeout(poll, 1000);
    };

    poll();
    return () => { active = false; };
  }, [documentId, onComplete]);

  if (!progress) {
    return (
      <div className="space-y-4 rounded-xl border border-border bg-surface p-6">
        <div className="mb-3 h-8 w-8 mx-auto animate-spin rounded-full border-4 border-accent-200 border-t-accent-600" />
        <p className="text-center text-foreground-muted">
          Indexing chunks for search...
        </p>
        <p className="text-center text-xs text-foreground-subtle">
          Generating embeddings and building the knowledge base — this can take
          a while for large books.
        </p>
      </div>
    );
  }

  const percent =
    progress.total_chunks > 0
      ? Math.round((progress.current_chunks / progress.total_chunks) * 100)
      : 0;

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}m ${s}s`;
  };

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-heading text-lg font-semibold">Indexing for search</h3>
        <span className="text-sm text-foreground-muted">
          {progress.total_chunks > 0
            ? `${progress.current_chunks} of ${progress.total_chunks} chunks`
            : "Preparing chunks..."}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-accent-500 transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="text-sm">
        <span className="text-foreground-muted">Elapsed</span>
        <p className="font-medium">{formatTime(progress.elapsed_sec || 0)}</p>
      </div>

      {progress.status === "embed_failed" && (
        <div className="rounded-lg bg-destructive-light p-3 text-sm text-destructive">
          Indexing failed: {progress.error || "Unknown error"}
        </div>
      )}
    </div>
  );
}
