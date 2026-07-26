"use client";

import { useState } from "react";

const DAYS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 7, label: "Sun" },
];

const TYPES = [
  { value: "vocabulary", label: "Vocabulary" },
  { value: "reading", label: "Reading" },
  { value: "grammar", label: "Grammar" },
  { value: "listening", label: "Listening" },
];

export function ScheduleBuilder() {
  const [name, setName] = useState("My Schedule");
  const [days, setDays] = useState<number[]>([1, 3, 5]);
  const [time, setTime] = useState("19:00");
  const [duration, setDuration] = useState(30);
  const [types, setTypes] = useState<string[]>(["vocabulary", "reading"]);
  const [itemCount, setItemCount] = useState(10);
  const [saved, setSaved] = useState(false);

  const toggleDay = (d: number) => {
    setDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));
  };

  const toggleType = (t: string) => {
    setTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  };

  const save = async () => {
    const token = localStorage.getItem("token");
    if (!token) return alert("Please log in first");

    const params = new URLSearchParams({
      name,
      days_of_week: days.join(","),
      time_of_day: time,
      duration_minutes: String(duration),
      content_types: types.join(","),
      daily_item_count: String(itemCount),
    });

    const res = await fetch(`/api/v1/schedules?${params}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setSaved(true);
  };

  return (
    <div className="space-y-6 rounded-xl border border-border bg-surface p-6 shadow-card">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-lg border border-border bg-background px-4 py-2 text-foreground"
        placeholder="Schedule name"
      />

      <div>
        <p className="mb-2 text-sm font-medium">Days</p>
        <div className="flex gap-2">
          {DAYS.map((d) => (
            <button
              key={d.value}
              onClick={() => toggleDay(d.value)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                days.includes(d.value)
                  ? "bg-primary-600 text-white"
                  : "border border-border bg-background text-foreground-muted"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <div>
          <label className="text-sm font-medium">Time</label>
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="mt-1 block rounded-lg border border-border bg-background px-3 py-2"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Duration (min)</label>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            min={5}
            max={120}
            className="mt-1 block w-24 rounded-lg border border-border bg-background px-3 py-2"
          />
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Content Types</p>
        <div className="flex gap-2">
          {TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => toggleType(t.value)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                types.includes(t.value)
                  ? "bg-accent-600 text-white"
                  : "border border-border bg-background text-foreground-muted"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={save}
        className="w-full rounded-lg bg-primary-600 py-3 font-medium text-white transition-colors hover:bg-primary-700"
      >
        {saved ? "Saved!" : "Save Schedule"}
      </button>
    </div>
  );
}
