"use client";

import { useMutation } from "@tanstack/react-query";
import { LoaderCircle, RotateCcw } from "lucide-react";
import { useState } from "react";

import { DocumentDropzone } from "@/components/documents/document-dropzone";
import { DocumentStatusTimeline } from "@/components/documents/document-status-timeline";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useDocumentPreparation } from "@/hooks/use-document-preparation";
import { getAPIErrorMessage } from "@/lib/api/client";
import { uploadDocument } from "@/lib/api/documents";
import { PREPARE_ACTION_LABEL } from "@/lib/terminology";
import type { KnowledgeDocument } from "@/types/document";

interface StepAddDocumentProps {
  workspaceId: string;
  knowledgeSpaceId: string;
  onReady: (document: KnowledgeDocument) => void;
}

export function StepAddDocument({
  workspaceId,
  knowledgeSpaceId,
  onReady,
}: StepAddDocumentProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploaded, setUploaded] = useState<KnowledgeDocument | null>(null);

  const preparation = useDocumentPreparation({
    organizationId: workspaceId,
    onReady,
  });

  const uploadMutation = useMutation({
    mutationFn: (selected: File) =>
      uploadDocument(workspaceId, knowledgeSpaceId, { file: selected }),
    onSuccess: (document) => {
      setUploaded(document);
      // Upload and preparation read as one action to the user, so start
      // preparing immediately rather than making them click twice.
      preparation.prepare(document.id);
    },
  });

  const isUploading = uploadMutation.isPending;
  const showTimeline = Boolean(uploaded);

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-[-0.02em] text-foreground">
        Add your first document
      </h2>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">
        Upload a policy, FAQ, or product doc. We&rsquo;ll read it and get it
        ready for questions.
      </p>

      {uploadMutation.isError ? (
        <Alert variant="destructive" className="mt-5">
          <AlertTitle>Upload failed</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(uploadMutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <DocumentDropzone
        className="mt-6"
        selectedFile={file}
        isUploading={isUploading}
        disabled={isUploading || preparation.isWorking}
        onFileSelected={(selected) => {
          setFile(selected);
          uploadMutation.mutate(selected);
        }}
        onClear={() => {
          setFile(null);
          setUploaded(null);
          preparation.reset();
          uploadMutation.reset();
        }}
      />

      {showTimeline ? (
        <div className="mt-6 rounded-lg border border-border bg-surface p-5">
          <p className="mb-4 text-sm font-medium text-foreground">
            {PREPARE_ACTION_LABEL}
          </p>
          <DocumentStatusTimeline
            status={preparation.status ?? uploaded?.status}
            errorMessage={preparation.errorMessage}
          />

          {preparation.timedOut ? (
            <p className="mt-3 text-xs leading-5 text-foreground-muted">
              This is taking longer than expected. The document may still be
              processing in the background.
            </p>
          ) : null}

          {preparation.hasFailed && uploaded ? (
            <Button
              className="mt-4"
              size="sm"
              variant="secondary"
              onClick={() => preparation.prepare(uploaded.id, true)}
            >
              <RotateCcw aria-hidden="true" />
              Try again
            </Button>
          ) : null}
        </div>
      ) : null}

      {preparation.isWorking && !preparation.hasFailed ? (
        /*
         * The second and last place with a voice. It can afford one here
         * because the timeline directly above already reports the literal
         * progress — this line is doing reassurance, not status.
         */
        <p className="mt-4 flex items-center gap-2 text-sm text-foreground-muted">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
          Reading it properly, so it can quote you later.
        </p>
      ) : null}
    </div>
  );
}
