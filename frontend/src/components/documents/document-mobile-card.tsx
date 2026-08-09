"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/common/status-badge";
import { DeleteDocumentAction } from "@/components/documents/delete-document-action";
import { DocumentActions } from "@/components/documents/document-actions";
import { ViewDocumentAction } from "@/components/documents/view-document-action";
import { formatRelativeDate } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types/document";

interface DocumentMobileCardProps {
  workspaceId: string;
  document: KnowledgeDocument;
  knowledgeSpaceName?: string;
  onPrepare: (documentId: string, force?: boolean) => void;
  isSubmitting?: boolean;
  onDelete: (documentId: string) => void;
  isDeleting?: boolean;
}

/** Stacked presentation of a table row, for viewports too narrow to scan columns. */
export function DocumentMobileCard({
  workspaceId,
  document,
  knowledgeSpaceName,
  onPrepare,
  isSubmitting,
  onDelete,
  isDeleting,
}: DocumentMobileCardProps) {
  return (
    <li className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start gap-2.5">
        <FileText
          aria-hidden="true"
          className="mt-0.5 size-4 shrink-0 text-foreground-subtle"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {document.title}
          </p>
          <p className="mt-0.5 text-xs text-foreground-subtle">
            <Link
              href={`/dashboard/knowledge/${document.knowledge_base_id}`}
              className="underline-offset-4 hover:text-foreground hover:underline"
            >
              {knowledgeSpaceName ?? "Knowledge space"}
            </Link>
            {" · "}
            {formatRelativeDate(document.created_at)}
          </p>
        </div>
        <StatusBadge status={document.status} />
      </div>

      {document.error_message ? (
        <p className="mt-2 text-xs leading-5 text-danger">
          {document.error_message}
        </p>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <DocumentActions
          className="flex-1"
          document={document}
          onPrepare={onPrepare}
          isSubmitting={isSubmitting}
        />
        <ViewDocumentAction workspaceId={workspaceId} document={document} />
        <DeleteDocumentAction
          document={document}
          onDelete={onDelete}
          isDeleting={isDeleting}
        />
      </div>
    </li>
  );
}
