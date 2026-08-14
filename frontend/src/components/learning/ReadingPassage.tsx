"use client";

import { ChoiceExercise } from "./ChoiceExercise";
import type { ItemProps } from "./types";

/** Reading comprehension: a passage plus four choices (or a legacy text input). */
export function ReadingPassage({ item, onSubmit, onNext }: ItemProps) {
  const data = item.data;
  const passage = data?.passage || item.question;

  return (
    <ChoiceExercise
      options={data?.options}
      correctIndex={data?.correct_index}
      onSubmit={onSubmit}
      onNext={onNext}
      textInput={{ placeholder: "Type your answer...", submitLabel: "Submit Answer" }}
    >
      <div className="rounded-xl border border-border bg-reading-bg p-6 shadow-card">
        <p className="mb-2 text-sm font-medium uppercase text-foreground-muted">Reading</p>
        <p className="font-body text-lg leading-relaxed text-reading-text">{passage}</p>
      </div>
    </ChoiceExercise>
  );
}
