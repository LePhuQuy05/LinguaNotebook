"use client";

import { useEffect, useState } from "react";

interface ParseProgressProps {
  documentId: string;
  onComplete?: () => void;
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

export function ParseProgress({ documentId, onComplete }: ParseProgressProps) {
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    const url = `/api/v1/documents/${documentId}/parse/progress`;
    const token = localStorage.getItem("token");

    const eventSource = new EventSource(
      `${url}?token=${encodeURIComponent(token || "")}`
    );

    eventSource.onmessage = (event) => {
      const data: ProgressData = JSON.parse(event.data);
      setProgress(data);

      if (data.status === "completed" || data.status === "completed_with_errors") {
        eventSource.close();
        onComplete?.();
      }
      if (data.status === "failed") {
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => eventSource.close();
  }, [documentId, onComplete]);

  if (!progress) {
    return (
      <div className="p-6 text-center text-foreground-muted">
        Connecting to parse stream...
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
          <p className="font-medium">{formatTime(progress.elapsed_sec)}</p>
        </div>
        <div>
          <span className="text-foreground-muted">ETA</span>
          <p className="font-medium">{formatTime(progress.eta_sec)}</p>
        </div>
        <div>
          <span className="text-foreground-muted">Speed</span>
          <p className="font-medium">
            {progress.pages_per_sec.toFixed(2)} p/s
          </p>
        </div>
      </div>

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
