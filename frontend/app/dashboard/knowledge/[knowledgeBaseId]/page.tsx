"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, CircleDashed, FileText, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { StatusBadge } from "@/components/common/status-badge";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { DeleteDocumentAction } from "@/components/documents/delete-document-action";
import { DocumentActions } from "@/components/documents/document-actions";
import { ViewDocumentAction } from "@/components/documents/view-document-action";
import { DocumentDropzone } from "@/components/documents/document-dropzone";
import { DeleteKnowledgeSpaceAction } from "@/components/knowledge/delete-knowledge-space-action";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useDocuments } from "@/hooks/use-documents";
import { useWorkspace } from "@/hooks/use-workspace";
import { getAPIErrorMessage } from "@/lib/api/client";
import { uploadDocument } from "@/lib/api/documents";
import { getKnowledgeBase } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { isDocumentReady } from "@/lib/terminology";
import { formatRelativeDate } from "@/lib/utils";

export default function KnowledgeSpaceDetailPage() {
  const params = useParams<{ knowledgeBaseId: string }>();
  const knowledgeSpaceId = params.knowledgeBaseId;
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;
  const queryClient = useQueryClient();

  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const knowledgeSpaceQuery = useQuery({
    queryKey: queryKeys.knowledgeBase(workspaceId, knowledgeSpaceId),
    queryFn: () => getKnowledgeBase(workspaceId!, knowledgeSpaceId),
    enabled: Boolean(workspaceId && knowledgeSpaceId),
  });

  const {
    documents,
    isLoading: documentsLoading,
    isError: documentsError,
    refetch: refetchDocuments,
    prepare,
    preparingDocumentId,
    remove,
    deletingDocumentId,
  } = useDocuments({ workspaceId, knowledgeSpaceId });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      uploadDocument(workspaceId!, knowledgeSpaceId, { file }),
    onSuccess: async (document) => {
      setPendingFile(null);
      await refetchDocuments();
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
      // Uploading and preparing read as one action, so start immediately
      // rather than making the user find the button afterwards.
      prepare(document.id);
      toast.success("Document uploaded. Preparing it for chat.");
    },
    onError: (error) => {
      setPendingFile(null);
      toast.error(getAPIErrorMessage(error));
    },
  });

  const knowledgeSpace = knowledgeSpaceQuery.data;
  const readyCount = documents.filter((document) =>
    isDocumentReady(document.status),
  ).length;
  const isReady = readyCount > 0;

  if (knowledgeSpaceQuery.isPending) {
    return <LoadingSkeleton variant="detail" rows={3} />;
  }

  if (knowledgeSpaceQuery.isError || !knowledgeSpace) {
    return (
      <div className="space-y-6">
        <Button asChild size="sm" variant="ghost" className="-ml-2">
          <Link href="/dashboard/knowledge">
            <ArrowLeft aria-hidden="true" />
            Knowledge
          </Link>
        </Button>
        <ErrorState
          title="We couldn’t load this knowledge space"
          message="It may have been removed, or the API may be unavailable."
          onRetry={() => void knowledgeSpaceQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div>
        <Button asChild size="sm" variant="ghost" className="-ml-2 mb-2">
          <Link href="/dashboard/knowledge">
            <ArrowLeft aria-hidden="true" />
            Knowledge
          </Link>
        </Button>

        <PageHeader
          title={knowledgeSpace.name}
          description={knowledgeSpace.description ?? undefined}
          actions={
            <div className="flex items-center gap-1">
              {isReady ? (
                <Button asChild>
                  <Link
                    href={`/dashboard/chat?knowledgeSpace=${encodeURIComponent(
                      knowledgeSpace.id,
                    )}`}
                  >
                    <Sparkles aria-hidden="true" />
                    Ask AI
                  </Link>
                </Button>
              ) : null}
              {workspaceId ? (
                <DeleteKnowledgeSpaceAction
                  workspaceId={workspaceId}
                  knowledgeSpace={knowledgeSpace}
                  redirectTo="/dashboard/knowledge"
                />
              ) : null}
            </div>
          }
        />

        <p
          className={
            isReady
              ? "mt-3 inline-flex items-center gap-1.5 text-sm text-success"
              : "mt-3 inline-flex items-center gap-1.5 text-sm text-foreground-subtle"
          }
        >
          {isReady ? (
            <Check aria-hidden="true" className="size-4" />
          ) : (
            <CircleDashed aria-hidden="true" className="size-4" />
          )}
          {isReady
            ? `${readyCount} of ${documents.length} ${
                documents.length === 1 ? "document" : "documents"
              } ready for chat`
            : "No documents are ready for chat yet"}
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-foreground">
            Add knowledge
          </h2>
          <p className="text-sm text-foreground-muted">
            Upload a document and we&rsquo;ll prepare it for chat automatically.
          </p>
        </CardHeader>
        <CardContent>
          <DocumentDropzone
            selectedFile={pendingFile}
            isUploading={uploadMutation.isPending}
            disabled={uploadMutation.isPending}
            onFileSelected={(file) => {
              setPendingFile(file);
              uploadMutation.mutate(file);
            }}
            onClear={() => setPendingFile(null)}
          />
        </CardContent>
      </Card>

      <section aria-labelledby="documents-heading" className="space-y-4">
        <h2
          id="documents-heading"
          className="text-base font-semibold text-foreground"
        >
          Documents
        </h2>

        {documentsLoading ? (
          <LoadingSkeleton rows={3} />
        ) : documentsError ? (
          <ErrorState
            title="We couldn’t load these documents"
            onRetry={() => void refetchDocuments()}
          />
        ) : documents.length === 0 ? (
          <EmptyState
            compact
            icon={FileText}
            title="No documents yet"
            description="Upload a PDF, FAQ, policy, or product doc to prepare your assistant."
          />
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
            {documents.map((document) => (
              <li
                key={document.id}
                className="flex flex-wrap items-center gap-3 p-4"
              >
                <FileText
                  aria-hidden="true"
                  className="size-4 shrink-0 text-foreground-subtle"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {document.title}
                  </p>
                  <p className="mt-0.5 text-xs text-foreground-subtle">
                    {formatRelativeDate(document.created_at)}
                  </p>
                  {document.error_message ? (
                    <p className="mt-1 text-xs leading-5 text-danger">
                      {document.error_message}
                    </p>
                  ) : null}
                </div>
                <StatusBadge status={document.status} />
                <DocumentActions
                  document={document}
                  onPrepare={prepare}
                  isSubmitting={preparingDocumentId === document.id}
                />
                <ViewDocumentAction
                  workspaceId={workspaceId!}
                  document={document}
                />
                <DeleteDocumentAction
                  document={document}
                  onDelete={remove}
                  isDeleting={deletingDocumentId === document.id}
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
