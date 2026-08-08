"use client";

import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import type { KnowledgeSpace } from "@/types/knowledge";

interface KnowledgeSpaceSelectProps {
  knowledgeSpaces: KnowledgeSpace[];
  value: string | null;
  onChange: (knowledgeSpaceId: string) => void;
  className?: string;
}

/**
 * A native select rather than a custom menu: it is a single-choice control in
 * a dense toolbar, and the native version is keyboard and screen-reader
 * correct for free, plus it uses the platform picker on mobile.
 */
export function KnowledgeSpaceSelect({
  knowledgeSpaces,
  value,
  onChange,
  className,
}: KnowledgeSpaceSelectProps) {
  return (
    <div className={cn("relative", className)}>
      <label htmlFor="chat-knowledge-space" className="sr-only">
        Knowledge space
      </label>
      <select
        id="chat-knowledge-space"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        disabled={knowledgeSpaces.length <= 1}
        className="h-9 w-full appearance-none truncate rounded-md border border-input bg-surface py-1 pl-3 pr-8 text-sm font-medium text-foreground outline-none transition-colors focus-visible:border-input focus-visible:ring-2 focus-visible:ring-ring/10 disabled:cursor-default disabled:opacity-100"
      >
        {knowledgeSpaces.map((knowledgeSpace) => (
          <option key={knowledgeSpace.id} value={knowledgeSpace.id}>
            {knowledgeSpace.name}
          </option>
        ))}
      </select>
      {knowledgeSpaces.length > 1 ? (
        <ChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-foreground-subtle"
        />
      ) : null}
    </div>
  );
}
