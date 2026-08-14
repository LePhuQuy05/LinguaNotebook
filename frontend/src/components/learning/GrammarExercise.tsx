"use client";

import { ChoiceExercise } from "./ChoiceExercise";
import type { ItemProps } from "./types";

/** Grammar: a fill-in-the-blank sentence plus four choices (or legacy text input). */
export function GrammarExercise({ item, onSubmit, onNext }: ItemProps) {
  const data = item.data;
  const prompt = data?.prompt || data?.pattern || item.question;

  return (
    <ChoiceExercise
      options={data?.options}
      correctIndex={data?.correct_index}
      onSubmit={onSubmit}
      onNext={onNext}
      textInput={{ placeholder: "Type the missing word or phrase...", submitLabel: "Check Answer" }}
    >
      <div className="rounded-xl border border-border bg-surface p-6 shadow-card">
        <p className="mb-2 text-sm font-medium uppercase text-foreground-muted">
          Fill in the blank
        </p>
        <p className="text-lg text-foreground">{prompt}</p>
      </div>
    </ChoiceExercise>
  );
}
