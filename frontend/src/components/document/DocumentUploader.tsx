"use client";

import { useState, useCallback } from "react";
import { Upload, FileText } from "lucide-react";

interface DocumentUploaderProps {
  onUploadComplete?: (documentId: string) => void;
}

export function DocumentUploader({ onUploadComplete }: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageStart, setPageStart] = useState(1);
  const [pageEnd, setPageEnd] = useState("");
  const [dpi, setDpi] = useState(100);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are supported");
        return;
      }
      if (file.size > 524_288_000) {
        setError("File exceeds 500MB maximum");
        return;
      }

      setUploading(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const params = new URLSearchParams({
          dpi: String(dpi),
          page_start: String(pageStart),
        });
        if (pageEnd) params.set("page_end", pageEnd);

        const res = await fetch(`/api/v1/documents/upload?${params}`, {
          method: "POST",
          body: formData,
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();
        onUploadComplete?.(data.document_id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete],
  );

  return (
    <div className="space-y-4">
      {/* Page range & DPI controls — outside dropzone */}
      <div className="flex items-center justify-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <label className="font-medium text-slate-600">Pages:</label>
          <input
            type="number" min={1} value={pageStart}
            onChange={(e) => setPageStart(Number(e.target.value))}
            className="w-20 rounded-lg border border-slate-200 px-3 py-2 text-center text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
            placeholder="1"
          />
          <span className="text-slate-400">–</span>
          <input
            type="number" min={1} value={pageEnd}
            onChange={(e) => setPageEnd(e.target.value)}
            className="w-20 rounded-lg border border-slate-200 px-3 py-2 text-center text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
            placeholder="end"
          />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label className="font-medium text-slate-600">DPI:</label>
          <select
            value={dpi}
            onChange={(e) => setDpi(Number(e.target.value))}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value={72}>72 (fast)</option>
            <option value={100}>100 (default)</option>
            <option value={150}>150 (dense)</option>
            <option value={200}>200 (small text)</option>
          </select>
        </div>
      </div>

      {/* Dropzone */}
      <div
        className={`relative rounded-xl border-2 border-dashed p-12 text-center transition-all duration-200 ${
          isDragging
            ? "border-primary-400 bg-primary-50"
            : "border-slate-200 hover:border-primary-300"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleUpload(file);
        }}
      >
        <input
          type="file"
          accept=".pdf"
          className="absolute inset-0 cursor-pointer opacity-0"
          onChange={(e) => { const file = e.target.files?.[0]; if (file) handleUpload(file); }}
        />
        <div className="flex flex-col items-center gap-3">
          {uploading ? (
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
          ) : (
            <Upload className="h-12 w-12 text-primary-400" />
          )}
          <div>
            <p className="text-lg font-medium text-slate-700">
              {uploading ? "Uploading..." : "Drop your PDF here"}
            </p>
            <p className="text-sm text-slate-400">or click to browse — up to 500MB</p>
          </div>
        </div>
      </div>
      {error && (
        <p className="mt-4 text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
