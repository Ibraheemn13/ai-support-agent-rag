"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileWarning, LoaderCircle } from "lucide-react";
import { useEffect, useMemo } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { APIError } from "@/lib/api/client";
import { fetchDocumentFile } from "@/lib/api/documents";
import { queryKeys } from "@/lib/query-keys";
import type { KnowledgeDocument } from "@/types/document";

/**
 * How a media type is shown. `docx` has no browser renderer, so it is offered
 * as a download rather than pretending a preview is coming.
 */
function previewKind(contentType: string): "pdf" | "text" | "download" {
  if (contentType === "application/pdf") return "pdf";
  if (contentType.startsWith("text/")) return "text";
  return "download";
}

interface DocumentPreviewDialogProps {
  workspaceId: string;
  document: KnowledgeDocument;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentPreviewDialog({
  workspaceId,
  document,
  open,
  onOpenChange,
}: DocumentPreviewDialogProps) {
  const {
    data: file,
    isPending,
    error,
  } = useQuery({
    queryKey: queryKeys.documentFile(workspaceId, document.id),
    queryFn: () => fetchDocumentFile(workspaceId, document.id),
    // Only fetched when someone actually opens the dialog: this is the one
    // request in the app that pulls a whole file over the wire.
    enabled: open,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const fileName = document.file_name ?? document.title;
  const kind = file ? previewKind(file.contentType) : null;

  // Derived from the blob rather than stored, so there is no render where the
  // URL and the blob it points at disagree.
  const objectUrl = useMemo(
    () => (file ? URL.createObjectURL(file.blob) : null),
    [file],
  );

  // An object URL pins its blob in memory until it is revoked.
  useEffect(() => {
    if (!objectUrl) return;
    return () => URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  const { data: text } = useQuery({
    queryKey: [...queryKeys.documentFile(workspaceId, document.id), "text"],
    queryFn: () => file!.blob.text(),
    enabled: Boolean(file) && kind === "text",
    staleTime: Infinity,
  });
  // 410 is the row outliving its bytes, which is a different thing to say than
  // a generic failure — the document is still here and still answerable.
  const isGone = error instanceof APIError && error.status === 410;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-3rem)] w-[calc(100%-2rem)] max-w-4xl flex-col">
        <DialogHeader>
          <DialogTitle className="truncate">{document.title}</DialogTitle>
          <DialogDescription className="truncate">
            {fileName}
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-72 flex-1 overflow-hidden rounded-lg border border-border bg-surface-subtle">
          {isPending ? (
            <p className="flex h-full min-h-72 items-center justify-center gap-2 text-sm text-foreground-muted">
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
              Opening the original file…
            </p>
          ) : error ? (
            <div className="flex h-full min-h-72 flex-col items-center justify-center gap-2 px-6 text-center">
              <FileWarning
                aria-hidden="true"
                className="size-6 text-foreground-subtle"
              />
              <p className="text-sm font-medium text-foreground">
                {isGone
                  ? "The original file isn’t stored any more"
                  : "We couldn’t open this file"}
              </p>
              <p className="max-w-sm text-sm leading-6 text-foreground-muted">
                {isGone
                  ? "Its passages are still prepared, so the assistant can still answer from this document."
                  : error.message}
              </p>
            </div>
          ) : kind === "pdf" && objectUrl ? (
            <iframe
              className="size-full min-h-72"
              src={objectUrl}
              title={`${document.title}, original file`}
            />
          ) : kind === "text" ? (
            <pre className="size-full max-h-[60vh] overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-6 text-foreground">
              {text}
            </pre>
          ) : (
            <div className="flex h-full min-h-72 flex-col items-center justify-center gap-2 px-6 text-center">
              <FileWarning
                aria-hidden="true"
                className="size-6 text-foreground-subtle"
              />
              <p className="text-sm font-medium text-foreground">
                This file type can’t be shown in the browser
              </p>
              <p className="text-sm leading-6 text-foreground-muted">
                Download it to read it in the app it came from.
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button asChild disabled={!objectUrl} variant="secondary">
            <a download={fileName} href={objectUrl ?? undefined}>
              <Download aria-hidden="true" />
              Download
            </a>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
