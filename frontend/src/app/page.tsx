import Link from "next/link";
import { BookOpen, Sparkles, Globe, Download } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col">
      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-4 py-1.5 text-sm font-medium text-primary-700">
          <Sparkles className="h-4 w-4" />
          100% free & open source
        </div>

        <h1 className="font-heading text-display-lg text-slate-900">
          Learn languages from{" "}
          <span className="bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
            your own documents
          </span>
        </h1>

        <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-500">
          Upload your foreign-language PDFs. LinguaNotebook parses them,
          builds a smart knowledge base, and creates personalized daily
          lessons — flashcards, reading, grammar, and listening.
        </p>

        <div className="mt-10 flex items-center gap-4">
          <Link
            href="/register"
            className="rounded-xl bg-gradient-to-r from-primary-600 to-primary-500 px-8 py-3.5 text-lg font-semibold text-white shadow-lg shadow-primary-200 transition-all duration-200 hover:shadow-xl hover:shadow-primary-300 hover:translate-y-[-1px] active:translate-y-0"
          >
            Get Started Free
          </Link>
          <Link
            href="/login"
            className="rounded-xl border-2 border-slate-200 bg-white px-8 py-3.5 text-lg font-semibold text-slate-700 transition-all duration-200 hover:border-primary-300 hover:text-primary-600"
          >
            Sign In
          </Link>
        </div>
      </section>

      {/* Features grid */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: BookOpen, title: "Parse PDFs", desc: "Upload textbooks, articles, novels in any language. HPD AI parses every page into structured text." },
            { icon: Sparkles, title: "Daily Lessons", desc: "Auto-generated flashcards, reading, grammar, and listening — from your own materials." },
            { icon: Globe, title: "Multilingual TTS", desc: "Hear any word or passage in 8+ languages. Works offline with cached audio." },
            { icon: Download, title: "Offline First", desc: "Complete lessons without internet. Syncs progress when you reconnect." },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md hover:border-primary-100 hover:translate-y-[-2px]"
            >
              <div className="mb-4 inline-flex rounded-xl bg-primary-50 p-3 text-primary-600 group-hover:bg-primary-100 transition-colors">
                <Icon className="h-6 w-6" />
              </div>
              <h3 className="mb-2 font-heading text-lg font-semibold text-slate-900">{title}</h3>
              <p className="text-sm leading-relaxed text-slate-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
