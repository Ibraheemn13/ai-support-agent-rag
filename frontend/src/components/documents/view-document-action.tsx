"use client";

import { Eye } from "lucide-react";
import { useState } from "react";

import { DocumentPreviewDialog } from "@/components/documents/document-preview-dialog";
import { Button } from "@/components/ui/button";
import type { KnowledgeDocument } from "@/types/document";

interface ViewDocumentActionProps {
  workspaceId: string;
  document: KnowledgeDocument;
  className?: string;
}

/**
 * Opens the original upload for reading.
 *
 * Offered at every status, including failed: seeing what was actually in the
 * file is usually how someone works out why it could not be prepared.
 *
 * The dialog is mounted lazily rather than rendered alongside every row —
 * unlike the delete dialog, opening this one fetches a whole file, so it must
 * not exist until it is asked for.
 */
export function ViewDocumentAction({
  workspaceId,
  document,
  className,
}: ViewDocumentActionProps) {
  const [open, setOpen] = useState(false);
  const [everOpened, setEverOpened] = useState(false);

  return (
    <>
      <Button
        size="icon"
        variant="ghost"
        className={className}
        title="View original file"
        onClick={() => {
          setEverOpened(true);
          setOpen(true);
        }}
      >
        <Eye aria-hidden="true" />
        <span className="sr-only">View {document.title}</span>
      </Button>

      {everOpened ? (
        <DocumentPreviewDialog
          workspaceId={workspaceId}
          document={document}
          open={open}
          onOpenChange={setOpen}
        />
      ) : null}
    </>
  );
}
