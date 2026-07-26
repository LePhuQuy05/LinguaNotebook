"use client";

import Link from "next/link";
import { BookOpen, BarChart3, Calendar } from "lucide-react";
import { SearchBar } from "../document/SearchBar";

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-surface/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <Link href="/" className="font-heading text-xl font-bold text-primary-600">
          LinguaNotebook
        </Link>

        <div className="flex-1">
          <SearchBar />
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/documents"
            className="flex items-center gap-1.5 text-sm font-medium text-foreground-muted transition-colors hover:text-foreground"
          >
            <BookOpen className="h-4 w-4" />
            Documents
          </Link>
          <Link
            href="/learning"
            className="flex items-center gap-1.5 text-sm font-medium text-foreground-muted transition-colors hover:text-foreground"
          >
            <Calendar className="h-4 w-4" />
            Today's Lesson
          </Link>
          <Link
            href="/progress"
            className="flex items-center gap-1.5 text-sm font-medium text-foreground-muted transition-colors hover:text-foreground"
          >
            <BarChart3 className="h-4 w-4" />
            Progress
          </Link>
        </div>
      </div>
    </nav>
  );
}
