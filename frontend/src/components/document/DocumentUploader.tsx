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

        const res = await fetch("/api/v1/documents/upload", {
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
    <div
      className={`relative rounded-xl border-2 border-dashed p-12 text-center transition-all duration-200 ${
        isDragging
          ? "border-primary-400 bg-primary-50"
          : "border-border hover:border-primary-300"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
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
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
      />
      <div className="flex flex-col items-center gap-3">
        {uploading ? (
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        ) : (
          <Upload className="h-12 w-12 text-primary-400" />
        )}
        <div>
          <p className="text-lg font-medium text-foreground">
            {uploading ? "Uploading..." : "Drop your PDF here"}
          </p>
          <p className="text-sm text-foreground-muted">
            or click to browse — up to 500MB
          </p>
        </div>
      </div>
      {error && (
        <p className="mt-4 text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
