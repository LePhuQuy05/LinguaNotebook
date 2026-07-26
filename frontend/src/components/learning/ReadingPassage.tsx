"use client";

import { useState } from "react";

interface ReadingPassageProps {
  item: { id: string; question: string; correct_answer: string };
  onSubmit: (response: string) => void;
}

export function ReadingPassage({ item, onSubmit }: ReadingPassageProps) {
  const [answer, setAnswer] = useState("");

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-reading-bg p-6 shadow-card">
        <p className="font-body text-lg leading-relaxed text-reading-text">
          {item.question}
        </p>
      </div>
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer..."
        rows={3}
        className="w-full rounded-lg border border-border bg-surface p-4 text-foreground placeholder:text-foreground-subtle focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
      />
      <button
        onClick={() => onSubmit(answer)}
        disabled={!answer.trim()}
        className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-50"
      >
        Submit Answer
      </button>
    </div>
  );
}
