"use client";

import { useState } from "react";
import { Play, Pause } from "lucide-react";

import { ChoiceExercise } from "./ChoiceExercise";
import type { ItemProps } from "./types";

/** Listening comprehension: a play button, the transcript, and four choices. */
export function ListeningExercise({ item, onSubmit, onNext }: ItemProps) {
  const [playing, setPlaying] = useState(false);
  const data = item.data;
  const transcript = data?.text || item.question;

  return (
    <ChoiceExercise
      options={data?.options}
      correctIndex={data?.correct_index}
      onSubmit={onSubmit}
      onNext={onNext}
      textInput={{
        placeholder: "What did you hear? Type your answer...",
        submitLabel: "Submit",
      }}
    >
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
        {data?.text && (
          <p className="mt-4 whitespace-pre-wrap rounded-lg bg-muted p-4 text-left text-foreground-subtle">
            {data.text}
          </p>
        )}
      </div>
    </ChoiceExercise>
  );
}
