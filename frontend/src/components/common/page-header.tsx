import * as React from "react";

import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0 max-w-3xl">
        {eyebrow ? (
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-foreground-subtle">
            {eyebrow}
          </p>
        ) : null}
        {/* The one place the display face appears inside the app. Page titles
            are the only in-app heading with room for it; card titles, table
            headers, and form labels stay on the UI sans. */}
        <h1 className="font-display text-2xl font-semibold text-foreground sm:text-[1.9rem]">
          {title}
        </h1>
        {description ? (
          <p className="mt-2 text-sm leading-6 text-foreground-muted sm:text-base">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
