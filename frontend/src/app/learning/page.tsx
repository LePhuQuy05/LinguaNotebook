"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Flashcard } from "../../components/learning/Flashcard";
import { ReadingPassage } from "../../components/learning/ReadingPassage";
import { GrammarExercise } from "../../components/learning/GrammarExercise";
import { ListeningExercise } from "../../components/learning/ListeningExercise";
import type { AnswerFeedback, LessonItemData } from "../../components/learning/types";

interface LessonSource {
  page_start: number;
  page_end: number;
  token_count: number | null;
  block_type: string;
  document_id: string;
  content: string;
}

interface LessonItem {
  id: string;
  item_type: string;
  order_index: number;
  question: string;
  correct_answer: string;
  data?: LessonItemData | null;
  completed: boolean;
  is_correct: boolean | null;
  source?: LessonSource | null;
}

interface Lesson {
  id: string;
  date: string;
  status: string;
  score: number | null;
  document_id: string | null;
  document_filename: string | null;
  chapter_num: number | null;
  chapter_title: string | null;
}

interface BookSummary {
  id: string;
  filename: string;
}

interface ChapterSummary {
  id: string;
  part: string | null;
  chapter_num: number;
  chapter_title: string;
  page_start: number;
  page_end: number;
}

export default function LearningPage() {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [items, setItems] = useState<LessonItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // Book → chapter picker (feature 009)
  const [pickerOpen, setPickerOpen] = useState(false);
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [selectedBook, setSelectedBook] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);
  const [chaptersLoading, setChaptersLoading] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch("/api/v1/lessons/daily", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.lesson) {
          setLesson(data.lesson);
          setItems(data.items || []);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // The picker's book list loads alongside the lesson.
  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch("/api/v1/documents", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setBooks(data.items || []))
      .catch(() => setBooks([]));
  }, []);

  // Selecting a book loads its curriculum map (chapter list).
  useEffect(() => {
    if (!selectedBook) {
      setChapters([]);
      return;
    }
    const token = localStorage.getItem("token");
    setChaptersLoading(true);
    fetch(`/api/v1/documents/${selectedBook}/structures`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((rows) => setChapters(rows || []))
      .catch(() => setChapters([]))
      .finally(() => setChaptersLoading(false));
  }, [selectedBook]);

  const submitAnswer = async (
    itemId: string,
    response: string,
    rating?: number,
  ): Promise<AnswerFeedback | null> => {
    if (!lesson) return null;
    const token = localStorage.getItem("token");
    const params = new URLSearchParams({ response });
    if (rating) params.set("self_rating", String(rating));
    try {
      const res = await fetch(
        `/api/v1/lessons/${lesson.id}/items/${itemId}/answer?${params}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      );
      return await res.json();
    } catch {
      return null;
    }
  };

  const completeLesson = async () => {
    if (!lesson) return;
    const token = localStorage.getItem("token");
    const res = await fetch(`/api/v1/lessons/${lesson.id}/complete`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setLesson({ ...lesson, status: "completed", score: data.score });
  };

  const handleNext = () => {
    if (currentIndex < items.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      completeLesson();
    }
  };

  const startChapterLesson = async (chapterId: string) => {
    const token = localStorage.getItem("token");
    setPickerError(null);
    try {
      const res = await fetch(`/api/v1/lessons/daily?chapter_id=${chapterId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.lesson) {
        setLesson(data.lesson);
        setItems(data.items || []);
        setCurrentIndex(0);
        setPickerOpen(false);
      } else {
        setPickerError(data.message || "No lesson could be created for that chapter.");
      }
    } catch {
      setPickerError("Could not start the lesson. Is the backend running?");
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="mt-6 h-64 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-center">
        <h1 className="font-heading text-heading-xl">No Lesson Today</h1>
        <p className="mt-4 text-foreground-muted">
          No active schedule for today. Create a schedule to get daily lessons.
        </p>
        <a
          href="/schedule"
          className="mt-6 inline-block rounded-lg bg-primary-600 px-6 py-3 text-white transition-colors hover:bg-primary-700"
        >
          Create Schedule
        </a>
      </div>
    );
  }

  if (lesson.status === "completed") {
    return (
      <div className="mx-auto max-w-2xl p-6 text-center">
        <h1 className="font-heading text-heading-xl">Lesson Complete! 🎉</h1>
        <p className="mt-4 text-2xl font-semibold text-primary-600">
          Score: {((lesson.score || 0) * 100).toFixed(0)}%
        </p>
        <p className="mt-2 text-foreground-muted">
          Great work! Come back tomorrow for your next lesson.
        </p>
      </div>
    );
  }

  const currentItem = items[currentIndex];
  if (!currentItem) return null;

  const progress = ((currentIndex + 1) / items.length) * 100;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* Book → chapter picker */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <button
          onClick={() => setPickerOpen(!pickerOpen)}
          className="flex w-full items-center justify-between text-sm font-medium text-foreground-muted transition-colors hover:text-foreground"
        >
          <span>📚 Pick a book and chapter</span>
          <span>{pickerOpen ? "▲" : "▼"}</span>
        </button>
        {pickerOpen && (
          <div className="mt-3 space-y-3">
            <select
              value={selectedBook ?? ""}
              onChange={(e) => setSelectedBook(e.target.value || null)}
              className="w-full rounded-lg border border-border bg-surface p-3 text-foreground focus:border-primary-500 focus:outline-none"
            >
              <option value="">Pick a book…</option>
              {books.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.filename}
                </option>
              ))}
            </select>
            {chaptersLoading && (
              <p className="text-sm text-foreground-muted">Loading chapters…</p>
            )}
            {!chaptersLoading && selectedBook && chapters.length === 0 && (
              <p className="text-sm text-foreground-muted">
                This book has no curriculum map yet.
              </p>
            )}
            {!chaptersLoading && chapters.length > 0 && (
              <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-border p-1">
                {chapters.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => startChapterLesson(c.id)}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors hover:bg-muted"
                  >
                    <span className="text-sm text-foreground">
                      Ch. {c.chapter_num} · {c.chapter_title}
                    </span>
                    <span className="text-xs text-foreground-subtle">
                      p.{c.page_start}
                      {c.page_end !== c.page_start ? `–${c.page_end}` : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}
            {pickerError && <p className="text-sm text-destructive">{pickerError}</p>}
          </div>
        )}
      </div>

      {/* Source attribution — which book/chapter this lesson comes from */}
      {lesson.chapter_title && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-foreground-muted">
            Today&apos;s chapter
          </p>
          <Link
            href={lesson.document_id ? `/documents/${lesson.document_id}` : "#"}
            className="mt-1 block font-heading text-lg font-semibold text-foreground transition-colors hover:text-primary-600"
          >
            Chapter {lesson.chapter_num} · {lesson.chapter_title}
          </Link>
          {lesson.document_filename && (
            <p className="mt-1 text-sm text-foreground-muted">
              from {lesson.document_filename}
            </p>
          )}
        </div>
      )}

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-foreground-muted">
          <span>
            {currentIndex + 1} of {items.length}
          </span>
          <span>{lesson.status}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary-600 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Item renderer — submit shows feedback, Next advances */}
      {currentItem.item_type === "flashcard" && (
        <Flashcard
          item={currentItem}
          onSubmit={(response, rating) => submitAnswer(currentItem.id, response, rating)}
          onNext={handleNext}
        />
      )}
      {currentItem.item_type === "reading" && (
        <ReadingPassage
          item={currentItem}
          onSubmit={(response) => submitAnswer(currentItem.id, response)}
          onNext={handleNext}
        />
      )}
      {currentItem.item_type === "grammar" && (
        <GrammarExercise
          item={currentItem}
          onSubmit={(response) => submitAnswer(currentItem.id, response)}
          onNext={handleNext}
        />
      )}
      {currentItem.item_type === "listening" && (
        <ListeningExercise
          item={currentItem}
          onSubmit={(response) => submitAnswer(currentItem.id, response)}
          onNext={handleNext}
        />
      )}

      {/* Source chunk this item was generated from */}
      {currentItem.source && (
        <details className="rounded-xl border border-border bg-surface p-4">
          <summary className="cursor-pointer select-none text-sm font-medium text-foreground-muted">
            View source
          </summary>
          <div className="mt-2 space-y-2 text-sm text-foreground-muted">
            <p>
              Pages {currentItem.source.page_start}
              {currentItem.source.page_end !== currentItem.source.page_start
                ? `–${currentItem.source.page_end}`
                : ""}
              {currentItem.source.token_count
                ? ` · ${currentItem.source.token_count} tokens`
                : ""}
              {currentItem.source.block_type
                ? ` · ${currentItem.source.block_type}`
                : ""}
            </p>
            <p className="whitespace-pre-wrap rounded bg-muted p-3 text-foreground-muted">
              {currentItem.source.content}
            </p>
          </div>
        </details>
      )}
    </div>
  );
}
