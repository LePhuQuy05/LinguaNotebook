"use client";

import { useState } from "react";
import { Play, Pause } from "lucide-react";

interface ListeningExerciseProps {
  item: { id: string; question: string; correct_answer: string };
  onSubmit: (response: string) => void;
}

export function ListeningExercise({ item, onSubmit }: ListeningExerciseProps) {
  const [playing, setPlaying] = useState(false);
  const [answer, setAnswer] = useState("");

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-surface p-8 shadow-card text-center">
        <button
          onClick={() => setPlaying(!playing)}
          className="mx-auto inline-flex h-20 w-20 items-center justify-center rounded-full bg-primary-100 text-primary-600 transition-all hover:bg-primary-200"
        >
          {playing ? <Pause className="h-10 w-10" /> : <Play className="h-10 w-10" />}
        </button>
        <p className="mt-4 text-sm text-foreground-muted">
          {playing ? "Playing..." : "Tap to listen"}
        </p>
      </div>
      <div className="rounded-xl border border-border bg-surface p-4">
        <p className="font-medium text-foreground">{item.question}</p>
      </div>
      <input
        type="text"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="What did you hear? Type your answer..."
        className="w-full rounded-lg border border-border bg-surface p-4 text-foreground placeholder:text-foreground-subtle focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
      />
      <button
        onClick={() => onSubmit(answer)}
        disabled={!answer.trim()}
        className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-50"
      >
        Submit
      </button>
    </div>
  );
}
