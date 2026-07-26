"use client";

import Link from "next/link";
import { BookOpen, Calendar, Sparkles } from "lucide-react";

export function Navbar() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-100 bg-white/80 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <Link href="/" className="flex items-center gap-2 font-heading text-xl font-bold text-primary-600">
          <Sparkles className="h-5 w-5" />
          LinguaNotebook
        </Link>

        <div className="flex flex-1 items-center justify-end gap-1">
          <Link
            href="/documents"
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <BookOpen className="h-4 w-4" />
            Documents
          </Link>
          <Link
            href="/learning"
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <Calendar className="h-4 w-4" />
            Study
          </Link>

          <div className="ml-3 border-l border-slate-200 pl-3">
            {token ? (
              <button
                onClick={() => { localStorage.clear(); window.location.href = "/"; }}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
              >
                Sign out
              </button>
            ) : (
              <Link
                href="/login"
                className="rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-primary-200 transition-all hover:shadow-lg hover:shadow-primary-300"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
