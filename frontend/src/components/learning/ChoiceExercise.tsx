"use client";

import { useState, type ReactNode } from "react";

import { FeedbackPanel } from "./AnswerFeedback";
import { OptionPicker } from "./OptionPicker";
import type { AnswerFeedback } from "./types";

interface TextInputConfig {
  placeholder: string;
  submitLabel: string;
}

interface ChoiceExerciseProps {
  /** The prompt card (passage / sentence / transcript), rendered by the caller. */
  children: ReactNode;
  /** Four answer choices; present → multiple choice, absent → text input. */
  options?: string[];
  correctIndex?: number;
  onSubmit: (response: string) => Promise<AnswerFeedback | null>;
  onNext: () => void;
  /** Text-input config for legacy items that carry no structured options. */
  textInput?: TextInputConfig;
}

/**
 * The reading/grammar/listening exercise skeleton: a stem card plus either
 * four clickable choices or a text input, and the submit → feedback → Next
 * state machine both paths share. The correct choice is highlighted once the
 * user submits, so a wrong pick shows the right answer inline.
 */
export function ChoiceExercise({
  children,
  options,
  correctIndex = 0,
  onSubmit,
  onNext,
  textInput,
}: ChoiceExerciseProps) {
  const [answer, setAnswer] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<AnswerFeedback | null>(null);

  const isMc = !!options && options.length === 4;

  const submitText = async () => {
    const result = await onSubmit(answer);
    if (result) setFeedback(result);
  };

  const submitOption = async (index: number) => {
    setSelected(index);
    const result = await onSubmit(String(index));
    if (result) setFeedback(result);
  };

  return (
    <div className="space-y-4">
      {children}

      {isMc ? (
        <>
          <OptionPicker
            options={options}
            correctIndex={correctIndex}
            selected={selected}
            disabled={selected !== null}
            onSelect={submitOption}
          />
          {feedback && <FeedbackPanel feedback={feedback} onNext={onNext} />}
        </>
      ) : feedback ? (
        <FeedbackPanel feedback={feedback} onNext={onNext} />
      ) : (
        textInput && (
          <>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder={textInput.placeholder}
              rows={3}
              className="w-full rounded-lg border border-border bg-surface p-4 text-foreground placeholder:text-foreground-subtle focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
            <button
              onClick={submitText}
              disabled={!answer.trim()}
              className="w-full rounded-lg bg-accent-600 py-3 font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-50"
            >
              {textInput.submitLabel}
            </button>
          </>
        )
      )}
    </div>
  );
}
