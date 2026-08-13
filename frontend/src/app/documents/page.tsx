"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Plus } from "lucide-react";
import { DocumentUploader } from "../../components/document/DocumentUploader";
import { ParseProgress } from "../../components/document/ParseProgress";

interface DocumentSummary {
  id: string;
  filename: string;
  total_pages: number | null;
  language: string | null;
  status: string;
  embed_status: string;
  chunks_count: number | null;
  created_at: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [parsingId, setParsingId] = useState<string | null>(null);
  const router = useRouter();

  const fetchDocuments = async () => {
    const token = localStorage.getItem("token");
    const res = await fetch("/api/v1/documents?per_page=50", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      setDocuments(data.items);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      uploading: "bg-muted text-foreground-muted",
      queued: "bg-primary-100 text-primary-700",
      parsing: "bg-accent-100 text-accent-700",
      completed: "bg-success-light text-success",
      completed_with_errors: "bg-yellow-100 text-yellow-700",
      failed: "bg-destructive-light text-destructive",
    };
    return (
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.uploading}`}
      >
        {status.replace(/_/g, " ")}
      </span>
    );
  };

  const embedBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: "bg-muted text-foreground-muted",
      embedding: "bg-accent-100 text-accent-700",
      embedded: "bg-success-light text-success",
      embed_failed: "bg-destructive-light text-destructive",
    };
    const label =
      status === "embedded"
        ? "indexed"
        : status === "embed_failed"
          ? "index failed"
          : status.replace(/_/g, " ");
    return (
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.pending}`}
      >
        {label}
      </span>
    );
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-heading-xl text-foreground">Documents</h1>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          Upload PDF
        </button>
      </div>

      {showUpload && (
        <DocumentUploader
          onUploadComplete={(id) => {
            setParsingId(id);
            setShowUpload(false);
            fetchDocuments();
          }}
        />
      )}

      {parsingId && (
        <ParseProgress
          documentId={parsingId}
          onComplete={() => {
            setParsingId(null);
            fetchDocuments();
          }}
        />
      )}

      {/* Document list */}
      {documents.length === 0 ? (
        <div className="py-16 text-center">
          <FileText className="mx-auto h-16 w-16 text-muted-foreground" />
          <p className="mt-4 text-lg text-foreground-muted">
            No documents yet. Upload your first PDF to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => router.push(`/documents/${doc.id}`)}
              className="flex w-full items-center gap-4 rounded-xl border border-border bg-surface p-4 text-left shadow-card transition-all hover:shadow-card-hover"
            >
              <FileText className="h-10 w-10 text-primary-400" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-foreground truncate">{doc.filename}</p>
                <p className="text-sm text-foreground-muted">
                  {doc.total_pages ? `${doc.total_pages} pages` : "—"}
                  {doc.language ? ` · ${doc.language}` : ""}
                  {" · "}
                  {new Date(doc.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                {statusBadge(doc.status)}
                {embedBadge(doc.embed_status)}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
