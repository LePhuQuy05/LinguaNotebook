/**
 * Shared types for lesson item components (feature 009).
 *
 * Structured items carry a `data` payload produced by the item generator
 * (rule or SLM); the shape matches the generator's per-type payloads:
 * flashcard {term, reading, definition, example}, reading/grammar/listening
 * {options[4], correct_index, …}. Legacy items — created before structured
 * payloads existed — have no `data` and fall back to a plain text input.
 */

export interface LessonItemData {
  // flashcard
  term?: string;
  reading?: string;
  definition?: string;
  example?: string;
  // reading
  passage?: string;
  // grammar
  pattern?: string;
  prompt?: string;
  // listening
  text?: string;
  audio_key?: string;
  // reading / grammar / listening
  options?: string[];
  correct_index?: number;
}

export interface LessonItemView {
  id: string;
  item_type: string;
  question: string;
  correct_answer: string;
  data?: LessonItemData | null;
}

/** The grading result returned by POST /lessons/{id}/items/{id}/answer. */
export interface AnswerFeedback {
  is_correct: boolean;
  correct_answer: string | null;
}

export interface ItemProps {
  item: LessonItemView;
  /** Submits the answer; null when the request failed (no feedback to show). */
  onSubmit: (response: string, rating?: number) => Promise<AnswerFeedback | null>;
  /** Advances to the next item (or completes the lesson). */
  onNext: () => void;
}
