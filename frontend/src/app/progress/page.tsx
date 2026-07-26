"use client";

import { useEffect, useState } from "react";
import { BarChart3, Flame, BookOpen, Clock } from "lucide-react";

export default function ProgressPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch("/api/v1/progress/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-center">
        <h1 className="font-heading text-heading-xl">Progress</h1>
        <p className="mt-4 text-foreground-muted">Log in and complete lessons to see your progress.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="font-heading text-heading-xl">Progress</h1>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4 shadow-card">
          <Flame className="h-8 w-8 text-streak" />
          <div>
            <p className="text-2xl font-bold">{data.current_streak}</p>
            <p className="text-sm text-foreground-muted">Day Streak</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4 shadow-card">
          <BookOpen className="h-8 w-8 text-primary-500" />
          <div>
            <p className="text-2xl font-bold">{data.total_words_learned}</p>
            <p className="text-sm text-foreground-muted">Words Learned</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4 shadow-card">
          <Clock className="h-8 w-8 text-accent-500" />
          <div>
            <p className="text-2xl font-bold">{data.total_study_minutes}</p>
            <p className="text-sm text-foreground-muted">Minutes Studied</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 shadow-card">
        <h3 className="mb-2 font-medium">Accuracy by Type</h3>
        <div className="space-y-2">
          {Object.entries(data.accuracy_by_type || {}).map(([key, val]: any) => (
            <div key={key} className="flex items-center gap-2">
              <span className="w-24 text-sm capitalize">{key}</span>
              <div className="h-3 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary-600"
                  style={{ width: `${(val || 0) * 100}%` }}
                />
              </div>
              <span className="text-sm text-foreground-muted">
                {val ? `${(val * 100).toFixed(0)}%` : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
