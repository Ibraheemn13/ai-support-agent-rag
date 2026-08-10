export const queryKeys = {
  currentUser: ["auth", "me"] as const,
  organizations: ["organizations"] as const,
  knowledgeBases: (organizationId: string | null | undefined) =>
    ["knowledge-bases", organizationId] as const,
  knowledgeBase: (
    organizationId: string | null | undefined,
    knowledgeBaseId: string,
  ) => ["knowledge-bases", organizationId, knowledgeBaseId] as const,
  /**
   * Filters are part of the key because they are part of the request now.
   * Two different searches are two different server results, and caching them
   * under one key would show the previous search's rows while the new one
   * loads.
   */
  documents: (
    organizationId: string | null | undefined,
    knowledgeBaseId?: string | null,
    filters?: { search?: string; statuses?: readonly string[] },
  ) =>
    [
      "documents",
      organizationId,
      knowledgeBaseId ?? "all",
      filters?.search ?? "",
      (filters?.statuses ?? []).join(","),
    ] as const,
  /**
   * The dashboard's five-row summary, kept off the paginated key on purpose.
   *
   * The document list is an infinite query, so its cache entry is
   * `{ pages, pageParams }`. A plain query sharing the key would store a bare
   * page there, and whichever hook read it second would find the wrong shape.
   */
  documentsSummary: (organizationId: string | null | undefined) =>
    ["documents-summary", organizationId] as const,
  document: (
    organizationId: string | null | undefined,
    documentId: string,
  ) => ["documents", organizationId, documentId] as const,
  documentFile: (
    organizationId: string | null | undefined,
    documentId: string,
  ) => ["documents", organizationId, documentId, "file"] as const,
  conversations: (organizationId: string | null | undefined) =>
    ["conversations", organizationId] as const,
  conversation: (
    organizationId: string | null | undefined,
    conversationId: string,
  ) => ["conversations", organizationId, conversationId] as const,
  conversationMessages: (
    organizationId: string | null | undefined,
    conversationId: string,
  ) => ["conversations", organizationId, conversationId, "messages"] as const,
};
