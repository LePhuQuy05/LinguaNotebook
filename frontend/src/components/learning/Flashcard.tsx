"use client";

import { useState } from "react";
import { Volume2 } from "lucide-react";

interface FlashcardProps {
  item: { id: string; question: string; correct_answer: string };
  onSubmit: (response: string, rating: number) => void;
}

export function Flashcard({ item, onSubmit }: FlashcardProps) {
  const [flipped, setFlipped] = useState(false);
  const [rating, setRating] = useState<number | null>(null);

  return (
    <div className="space-y-4">
      <div
        onClick={() => setFlipped(!flipped)}
        className="cursor-pointer rounded-2xl border border-border bg-surface p-8 shadow-card transition-all duration-300 hover:shadow-card-hover min-h-[300px] flex flex-col items-center justify-center"
      >
        {!flipped ? (
          <div className="text-center">
            <p className="text-heading-lg font-heading text-foreground">{item.question}</p>
            <p className="mt-4 text-sm text-foreground-muted">Tap to reveal answer</p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-lg text-foreground">{item.correct_answer}</p>
            <button className="mt-4 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm transition-colors hover:bg-muted">
              <Volume2 className="h-4 w-4" /> Play Audio
            </button>
          </div>
        )}
      </div>

      {flipped && (
        <div className="space-y-3">
          <p className="text-center text-sm font-medium text-foreground-muted">
            How well did you know this?
          </p>
          <div className="flex justify-center gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                onClick={() => setRating(n)}
                className={`h-10 w-10 rounded-full text-sm font-medium transition-all ${
                  rating === n
                    ? "bg-primary-600 text-white"
                    : "border border-border bg-surface text-foreground-muted hover:border-primary-300"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="flex justify-between text-xs text-foreground-subtle">
            <span>Forgot</span>
            <span>Easy</span>
          </div>
          {rating && (
            <button
              onClick={() => onSubmit("", rating)}
              className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700"
            >
              Next →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
