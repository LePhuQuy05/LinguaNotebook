"use client";

import type { AnswerFeedback } from "./types";

interface FeedbackPanelProps {
  feedback: AnswerFeedback;
  onNext: () => void;
}

/** Right/wrong verdict + the correct answer, then a Next button. */
export function FeedbackPanel({ feedback, onNext }: FeedbackPanelProps) {
  return (
    <div className="space-y-3">
      <div
        className={`rounded-xl border border-border p-4 ${
          feedback.is_correct
            ? "bg-success-light text-success"
            : "bg-destructive-light text-destructive"
        }`}
      >
        <p className="font-semibold">{feedback.is_correct ? "Correct! 🎉" : "Not quite"}</p>
        {!feedback.is_correct && feedback.correct_answer && (
          <p className="mt-1 text-sm text-foreground">
            Correct answer:{" "}
            <span className="font-semibold text-foreground">{feedback.correct_answer}</span>
          </p>
        )}
      </div>
      <button
        onClick={onNext}
        className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700"
      >
        Next →
      </button>
    </div>
  );
}
