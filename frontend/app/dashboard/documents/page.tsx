"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, LoaderCircle, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { DocumentMobileCard } from "@/components/documents/document-mobile-card";
import { DocumentTable } from "@/components/documents/document-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useDocuments } from "@/hooks/use-documents";
import { useWorkspace } from "@/hooks/use-workspace";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import {
  DOCUMENT_FILTERS,
  type DocumentFilterKey,
  documentFilterCount,
  documentFilterStatuses,
} from "@/lib/terminology";
import { cn } from "@/lib/utils";

export default function DocumentsPage() {
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;

  const [filter, setFilter] = useState<DocumentFilterKey>("all");
  const [search, setSearch] = useState("");
  // The request follows the search, one step behind the keyboard.
  const debouncedSearch = useDebouncedValue(search);

  const statuses = useMemo(() => documentFilterStatuses(filter), [filter]);

  const {
    documents,
    statusCounts,
    isLoading,
    isError,
    refetch,
    hasMore,
    loadMore,
    isLoadingMore,
    prepare,
    preparingDocumentId,
    remove,
    deletingDocumentId,
  } = useDocuments({
    workspaceId,
    search: debouncedSearch,
    statuses,
  });

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const knowledgeSpaceNames = useMemo(
    () =>
      new Map(
        (knowledgeSpacesQuery.data ?? []).map((space) => [space.id, space.name]),
      ),
    [knowledgeSpacesQuery.data],
  );

  const isFiltered = Boolean(debouncedSearch.trim()) || filter !== "all";
  // Distinguishes "nothing uploaded" from "nothing matches": the same empty
  // list means two different things, and only one of them is a dead end.
  const totalDocuments = documentFilterCount("all", statusCounts);

  return (
    <div className="space-y-7">
      <PageHeader
        title="Documents"
        description="Everything your assistant can draw on, across all knowledge spaces."
        actions={
          <Button asChild variant="secondary">
            <Link href="/dashboard/knowledge">Add knowledge</Link>
          </Button>
        }
      />

      {isError ? (
        <ErrorState
          title="We couldn’t load your documents"
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div
              role="group"
              aria-label="Filter by status"
              className="flex flex-wrap gap-1.5"
            >
              {DOCUMENT_FILTERS.map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={filter === key}
                  onClick={() => setFilter(key)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    filter === key
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-surface text-foreground-muted hover:bg-surface-hover",
                  )}
                >
                  {label}
                  <span className="ml-1.5 opacity-70">
                    {documentFilterCount(key, statusCounts)}
                  </span>
                </button>
              ))}
            </div>

            <div className="relative sm:w-64">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-foreground-subtle"
              />
              <Input
                type="search"
                aria-label="Search documents"
                placeholder="Search documents"
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          {isLoading ? (
            <LoadingSkeleton rows={4} />
          ) : documents.length === 0 ? (
            isFiltered ? (
              <EmptyState
                compact
                icon={Search}
                title="No matching documents"
                description="Try a different search term or filter."
                action={
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSearch("");
                      setFilter("all");
                    }}
                  >
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={FileText}
                title="No documents uploaded yet"
                description="Add PDFs, FAQs, policies, or product docs to prepare your assistant."
                action={
                  <Button asChild>
                    <Link href="/dashboard/knowledge">Upload document</Link>
                  </Button>
                }
              />
            )
          ) : (
            <>
              {/*
                Table only from xl. The fixed sidebar takes 240px, so at
                1024 the content column is ~736px and the five columns would
                have to scroll sideways. Cards read better than that.
              */}
              <div className="hidden xl:block">
                <DocumentTable
                  workspaceId={workspaceId!}
                  documents={documents}
                  knowledgeSpaceNames={knowledgeSpaceNames}
                  onPrepare={prepare}
                  preparingDocumentId={preparingDocumentId}
                  onDelete={remove}
                  deletingDocumentId={deletingDocumentId}
                />
              </div>

              <ul className="grid gap-3 xl:hidden">
                {documents.map((document) => (
                  <DocumentMobileCard
                    key={document.id}
                    workspaceId={workspaceId!}
                    document={document}
                    knowledgeSpaceName={knowledgeSpaceNames.get(
                      document.knowledge_base_id,
                    )}
                    onPrepare={prepare}
                    isSubmitting={preparingDocumentId === document.id}
                    onDelete={remove}
                    isDeleting={deletingDocumentId === document.id}
                  />
                ))}
              </ul>

              {hasMore ? (
                <div className="flex flex-col items-center gap-2">
                  <Button
                    variant="secondary"
                    disabled={isLoadingMore}
                    onClick={loadMore}
                  >
                    {isLoadingMore ? (
                      <LoaderCircle aria-hidden="true" className="animate-spin" />
                    ) : null}
                    Load more documents
                  </Button>
                  <p className="text-xs text-foreground-subtle">
                    Showing {documents.length} of {totalDocuments}
                  </p>
                </div>
              ) : null}
            </>
          )}
        </>
      )}
    </div>
  );
}
