"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/common/status-badge";
import { DeleteDocumentAction } from "@/components/documents/delete-document-action";
import { DocumentActions } from "@/components/documents/document-actions";
import { ViewDocumentAction } from "@/components/documents/view-document-action";
import { formatRelativeDate } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types/document";

interface DocumentTableProps {
  workspaceId: string;
  documents: KnowledgeDocument[];
  /** Maps knowledge space id to name, so no raw id reaches the page. */
  knowledgeSpaceNames: Map<string, string>;
  onPrepare: (documentId: string, force?: boolean) => void;
  preparingDocumentId?: string;
  onDelete: (documentId: string) => void;
  deletingDocumentId?: string;
}

/** Desktop presentation. The mobile card list renders the same data. */
export function DocumentTable({
  workspaceId,
  documents,
  knowledgeSpaceNames,
  onPrepare,
  preparingDocumentId,
  onDelete,
  deletingDocumentId,
}: DocumentTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full min-w-[52rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-border">
            <th
              scope="col"
              className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-foreground-subtle"
            >
              Title
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-foreground-subtle"
            >
              Knowledge space
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-foreground-subtle"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-foreground-subtle"
            >
              Uploaded
            </th>
            <th scope="col" className="px-4 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>

        <tbody className="divide-y divide-border">
          {documents.map((document) => (
            <tr key={document.id} className="hover:bg-surface-hover/60">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2.5">
                  <FileText
                    aria-hidden="true"
                    className="size-4 shrink-0 text-foreground-subtle"
                  />
                  <span className="max-w-[18rem] truncate text-sm font-medium text-foreground">
                    {document.title}
                  </span>
                </div>
                {document.error_message ? (
                  <p className="mt-1 max-w-[22rem] truncate text-xs text-danger">
                    {document.error_message}
                  </p>
                ) : null}
              </td>

              <td className="px-4 py-3">
                <Link
                  href={`/dashboard/knowledge/${document.knowledge_base_id}`}
                  className="text-sm text-foreground-muted underline-offset-4 hover:text-foreground hover:underline"
                >
                  {knowledgeSpaceNames.get(document.knowledge_base_id) ??
                    "Knowledge space"}
                </Link>
              </td>

              <td className="px-4 py-3">
                <StatusBadge status={document.status} />
              </td>

              <td className="whitespace-nowrap px-4 py-3 text-sm text-foreground-muted">
                {formatRelativeDate(document.created_at)}
              </td>

              <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-1">
                  <DocumentActions
                    document={document}
                    onPrepare={onPrepare}
                    isSubmitting={preparingDocumentId === document.id}
                  />
                  <ViewDocumentAction
                    workspaceId={workspaceId}
                    document={document}
                  />
                  <DeleteDocumentAction
                    document={document}
                    onDelete={onDelete}
                    isDeleting={deletingDocumentId === document.id}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
