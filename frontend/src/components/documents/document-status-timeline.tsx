import { AlertCircle, Check, LoaderCircle } from "lucide-react";

import {
  DOCUMENT_PREPARATION_STAGES,
  describeDocumentStatus,
  hasDocumentFailed,
  preparationStageIndex,
} from "@/lib/terminology";
import { cn } from "@/lib/utils";

interface DocumentStatusTimelineProps {
  status?: string | null;
  /** Shown under the failed step so the user knows what to fix. */
  errorMessage?: string | null;
  className?: string;
}

/**
 * Progress through preparation: Uploaded, Processing, Extracted, Ready.
 *
 * A failure is rendered as an interruption at the step that was reached rather
 * than as a fifth step, because users do not move through "failed" on the way
 * to anywhere.
 */
export function DocumentStatusTimeline({
  status,
  errorMessage,
  className,
}: DocumentStatusTimelineProps) {
  const failed = hasDocumentFailed(status);
  const currentIndex = preparationStageIndex(status);

  return (
    <div className={cn("space-y-0", className)}>
      <ol className="space-y-0">
        {DOCUMENT_PREPARATION_STAGES.map((stage, index) => {
          const { label } = describeDocumentStatus(stage);
          const isComplete = !failed && currentIndex > index;
          const isCurrent = !failed && currentIndex === index;
          const isFailedHere = failed && index === 0;
          const isLast = index === DOCUMENT_PREPARATION_STAGES.length - 1;

          return (
            <li key={stage} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium",
                    isComplete &&
                      "border-success bg-success text-success-foreground",
                    isCurrent &&
                      "border-warning bg-warning-surface text-warning",
                    isFailedHere && "border-danger bg-danger-surface text-danger",
                    !isComplete &&
                      !isCurrent &&
                      !isFailedHere &&
                      "border-border bg-surface text-foreground-subtle",
                  )}
                >
                  {isComplete ? (
                    <Check aria-hidden="true" className="size-3.5" />
                  ) : isCurrent ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="size-3.5 animate-spin"
                    />
                  ) : isFailedHere ? (
                    <AlertCircle aria-hidden="true" className="size-3.5" />
                  ) : (
                    index + 1
                  )}
                </span>
                {!isLast ? (
                  <span
                    aria-hidden="true"
                    className={cn(
                      "my-1 w-px flex-1",
                      isComplete ? "bg-success" : "bg-border",
                    )}
                  />
                ) : null}
              </div>

              <div className={cn("min-w-0 pb-4", isLast && "pb-0")}>
                <p
                  className={cn(
                    "text-sm font-medium",
                    isComplete || isCurrent
                      ? "text-foreground"
                      : "text-foreground-subtle",
                  )}
                >
                  {label}
                </p>
                {isCurrent ? (
                  <p className="mt-0.5 text-xs leading-5 text-foreground-muted">
                    {describeDocumentStatus(stage).description}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>

      {failed ? (
        <p className="mt-1 rounded-md border border-danger-border bg-danger-surface px-3 py-2 text-xs leading-5 text-danger">
          {errorMessage?.trim()
            ? errorMessage
            : "We couldn’t prepare this document. Try again, or upload a different file."}
        </p>
      ) : null}
    </div>
  );
}
