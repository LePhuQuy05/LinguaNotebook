"use client";

import { useEffect, useState } from "react";

interface ParseProgressProps {
  documentId: string;
  onComplete?: () => void;
  onCancel?: () => void;
}

interface ProgressData {
  status: string;
  current_page: number;
  total_pages: number;
  elapsed_sec: number;
  eta_sec: number;
  pages_per_sec: number;
  errors?: Array<{ page: number; message: string }>;
}

export function ParseProgress({ documentId, onComplete, onCancel }: ParseProgressProps) {
  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    setCancelling(true);
    await fetch(`/api/v1/documents/${documentId}/parse/cancel`, { method: "POST" });
    onCancel?.();
  };
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    let active = true;

    const poll = async () => {
      try {
        const res = await fetch(
          `/api/v1/documents/${documentId}/parse/progress/poll?token=${encodeURIComponent(token || "")}`,
        );
        if (!res.ok || !active) return;
        const data: ProgressData = await res.json();
        setProgress(data);

        if (data.status === "completed" || data.status === "completed_with_errors") {
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
      <div className="p-6 text-center text-foreground-muted">
        <div className="mb-3 h-8 w-8 mx-auto animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        Waiting for worker to pick up this job...
        <p className="mt-2 text-xs text-foreground-subtle">
          Make sure the Celery worker is running (GPU or CPU mode).
        </p>
      </div>
    );
  }

  const percent =
    progress.total_pages > 0
      ? Math.round((progress.current_page / progress.total_pages) * 100)
      : 0;

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}m ${s}s`;
  };

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-heading text-lg font-semibold">
          {progress.status === "running" ? "Parsing..." : progress.status}
        </h3>
        <span className="text-sm text-foreground-muted">
          Page {progress.current_page} of {progress.total_pages}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary-600 transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-foreground-muted">Elapsed</span>
          <p className="font-medium">{formatTime(progress.elapsed_sec || 0)}</p>
        </div>
        <div>
          <span className="text-foreground-muted">ETA</span>
          <p className="font-medium">{formatTime(progress.eta_sec || 0)}</p>
        </div>
        <div>
          <span className="text-foreground-muted">Speed</span>
          <p className="font-medium">
            {(progress.pages_per_sec || 0).toFixed(2)} p/s
          </p>
        </div>
      </div>

      {/* Cancel button */}
      {progress.status === "running" && (
        <button
          onClick={handleCancel}
          disabled={cancelling}
          className="w-full rounded-lg border border-red-200 bg-red-50 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-100 disabled:opacity-50"
        >
          {cancelling ? "Cancelling..." : "Cancel Parsing"}
        </button>
      )}

      {/* Errors */}
      {progress.errors && progress.errors.length > 0 && (
        <div className="rounded-lg bg-destructive-light p-3 text-sm text-destructive">
          <p className="font-medium">Errors on pages:</p>
          <ul className="list-inside list-disc">
            {progress.errors.map((e, i) => (
              <li key={i}>
                Page {e.page}: {e.message.slice(0, 100)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
