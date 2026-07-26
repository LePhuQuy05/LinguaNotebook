"use client";

import { useEffect, useState } from "react";
import { Flashcard } from "@/components/learning/Flashcard";
import { ReadingPassage } from "@/components/learning/ReadingPassage";
import { GrammarExercise } from "@/components/learning/GrammarExercise";
import { ListeningExercise } from "@/components/learning/ListeningExercise";

interface LessonItem {
  id: string;
  item_type: string;
  order_index: number;
  question: string;
  completed: boolean;
  is_correct: boolean | null;
}

interface Lesson {
  id: string;
  date: string;
  status: string;
  score: number | null;
}

export default function LearningPage() {
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [items, setItems] = useState<LessonItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);

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

  const submitAnswer = async (itemId: string, response: string, rating?: number) => {
    if (!lesson) return;
    const token = localStorage.getItem("token");
    const params = new URLSearchParams({ response });
    if (rating) params.set("self_rating", String(rating));
    await fetch(
      `/api/v1/lessons/${lesson.id}/items/${itemId}/answer?${params}`,
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
    );
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

      {/* Item renderer */}
      {currentItem.item_type === "flashcard" && (
        <Flashcard
          item={currentItem}
          onSubmit={(response, rating) => {
            submitAnswer(currentItem.id, response, rating);
            handleNext();
          }}
        />
      )}
      {currentItem.item_type === "reading" && (
        <ReadingPassage
          item={currentItem}
          onSubmit={(response) => {
            submitAnswer(currentItem.id, response);
            handleNext();
          }}
        />
      )}
      {currentItem.item_type === "grammar" && (
        <GrammarExercise
          item={currentItem}
          onSubmit={(response) => {
            submitAnswer(currentItem.id, response);
            handleNext();
          }}
        />
      )}
      {currentItem.item_type === "listening" && (
        <ListeningExercise
          item={currentItem}
          onSubmit={(response) => {
            submitAnswer(currentItem.id, response);
            handleNext();
          }}
        />
      )}
    </div>
  );
}
