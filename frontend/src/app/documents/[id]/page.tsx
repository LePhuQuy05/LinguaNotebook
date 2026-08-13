"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, FileText, Sparkles } from "lucide-react";
import Link from "next/link";
import { MarkdownContent } from "../../../components/document/MarkdownContent";
import { ParseProgress } from "../../../components/document/ParseProgress";
import { EmbedProgress } from "../../../components/document/EmbedProgress";
import { CurriculumMap } from "../../../components/document/CurriculumMap";

interface ContentBlock {
  id: string;
  page_number: number;
  block_type: string;
  content_markdown: string;
  bbox: number[] | null;
}

interface DocumentDetail {
  id: string;
  filename: string;
  total_pages: number | null;
  language: string | null;
  status: string;
  parse_method: string | null;
  error_message: string | null;
  embed_status: string;
  chunks_count: number | null;
  embedded_at: string | null;
  created_at: string;
  blocks: ContentBlock[];
}

interface ChapterStructure {
  id: string;
  part: string;
  chapter_num: number;
  chapter_title: string;
  page_start: number;
  page_end: number;
  order: number;
}

const blockColors: Record<string, string> = {
  header: "border-l-primary-500 bg-primary-50",
  paragraph: "border-l-muted-foreground",
  table: "border-l-accent-500 bg-accent-50",
  list: "border-l-amber-500 bg-amber-50",
  image_caption: "border-l-slate-400 bg-slate-50",
};

export default function DocumentViewerPage() {
  const params = useParams();
  const id = params.id as string;
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [structures, setStructures] = useState<ChapterStructure[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch(`/api/v1/documents/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setDoc(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));

    fetch(`/api/v1/documents/${id}/structures`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then(setStructures)
      .catch(() => setStructures([]));
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <div className="space-y-4">
          <div className="h-8 w-48 animate-pulse rounded bg-muted" />
          <div className="h-64 animate-pulse rounded-xl bg-muted" />
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-foreground-muted">Document not found.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/documents"
          className="rounded-lg p-2 text-foreground-muted transition-colors hover:bg-muted"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="font-heading text-heading-md text-foreground">
            {doc.filename}
          </h1>
          <p className="text-sm text-foreground-muted">
            {doc.total_pages ? `${doc.total_pages} pages` : "Parsing..."}
            {doc.language ? ` · ${doc.language}` : ""}
            {doc.parse_method
              ? ` · ${doc.parse_method === "text_layer" ? "📄 Text extraction" : "🔍 OCR"}`
              : ""}
          </p>
        </div>
      </div>

      {/* Show parse progress for queued/parsing docs (not for completed/failed/cancelled) */}
      {(doc.status === "queued" ||
        doc.status === "parsing" ||
        doc.status === "uploading") && (
        <ParseProgress
          documentId={id}
          onComplete={() => window.location.reload()}
        />
      )}

      {/* Embed / RAG indexing status */}
      {doc.embed_status === "embedding" && (
        <EmbedProgress
          documentId={id}
          onComplete={() => window.location.reload()}
        />
      )}
      {doc.embed_status === "embedded" && doc.chunks_count != null && (
        <div className="flex items-center gap-2 rounded-xl border border-border bg-success-light p-4 text-sm text-success">
          <Sparkles className="h-4 w-4 shrink-0" />
          <span>
            Indexed <strong>{doc.chunks_count}</strong> chunks for semantic
            search
            {doc.embedded_at
              ? ` · ${new Date(doc.embedded_at).toLocaleDateString()}`
              : ""}
            .
          </span>
        </div>
      )}
      {doc.embed_status === "embed_failed" && (
        <div className="rounded-xl border border-border bg-destructive-light p-4 text-sm text-destructive">
          Embedding failed — re-upload the document to rebuild the knowledge
          base.
        </div>
      )}

      {/* Cancelled state */}
      {doc.status === "failed" && doc.error_message === "Cancelled by user" && (
        <div className="py-16 text-center">
          <p className="text-slate-500">Parsing was cancelled.</p>
          <p className="mt-2 text-sm text-slate-400">
            Re-upload the document to try again.
          </p>
        </div>
      )}

      {/* Parse complete with no blocks */}
      {doc.status === "completed" && doc.blocks.length === 0 && (
        <div className="py-16 text-center">
          <FileText className="mx-auto h-16 w-16 text-muted-foreground" />
          <p className="mt-4 text-foreground-muted">
            No content blocks extracted.
          </p>
        </div>
      )}

      {/* Parsed content blocks */}
      {doc.blocks.length > 0 && (
        <div className="space-y-4">
          {doc.blocks.map((block) => (
            <div
              key={block.id}
              className={`rounded-r-lg border-l-4 bg-surface p-4 shadow-card ${
                blockColors[block.block_type] || "border-l-muted-foreground"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="text-xs font-medium uppercase text-foreground-muted">
                  {block.block_type}
                </span>
                <span className="text-xs text-foreground-subtle">
                  Page {block.page_number}
                </span>
              </div>
              <div className="prose prose-slate max-w-none font-body text-reading-text">
                <MarkdownContent content={block.content_markdown} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Failed state */}
      {doc.status === "failed" && (
        <div className="py-16 text-center">
          <p className="text-destructive">
            Parsing failed: {doc.error_message || "Unknown error"}
          </p>
        </div>
      )}

      {/* Curriculum map from the book's TOC */}
      <CurriculumMap structures={structures} />
    </div>
  );
}
