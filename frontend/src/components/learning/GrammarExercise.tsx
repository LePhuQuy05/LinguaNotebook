"use client";

import { useState } from "react";

interface GrammarExerciseProps {
  item: { id: string; question: string; correct_answer: string };
  onSubmit: (response: string) => void;
}

export function GrammarExercise({ item, onSubmit }: GrammarExerciseProps) {
  const [answer, setAnswer] = useState("");

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-surface p-6 shadow-card">
        <p className="mb-2 text-sm font-medium uppercase text-foreground-muted">
          Fill in the blank
        </p>
        <p className="text-lg text-foreground">{item.question}</p>
      </div>
      <input
        type="text"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type the missing word or phrase..."
        className="w-full rounded-lg border border-border bg-surface p-4 text-lg text-foreground placeholder:text-foreground-subtle focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
      />
      <button
        onClick={() => onSubmit(answer)}
        disabled={!answer.trim()}
        className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-50"
      >
        Check Answer
      </button>
    </div>
  );
}
