import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * The SupportMind mark.
 *
 * Three bars of decreasing length resolving into a single dot: several
 * documents narrowing to one answer. It is the hero diagram compressed to
 * 32×32, which is the point — the mark and the illustration should read as the
 * same idea at two scales rather than as two unrelated drawings.
 *
 * Drawn with four solid shapes and no strokes so that nothing thins out below
 * 20px. `app/icon.svg` is the same geometry with the colours baked in, because
 * a favicon cannot inherit tokens.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={cn("size-7", className)}
      viewBox="0 0 32 32"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect className="fill-primary" width="32" height="32" rx="8" />
      <g className="fill-primary-foreground">
        <rect x="7.5" y="8.6" width="12.5" height="2.9" rx="1.45" />
        <rect x="7.5" y="14.6" width="9.5" height="2.9" rx="1.45" />
        <rect x="7.5" y="20.6" width="6.5" height="2.9" rx="1.45" />
        <circle cx="22.8" cy="22.05" r="3.3" />
      </g>
    </svg>
  );
}

interface WordmarkProps {
  /** Where the mark links to; omit to render it as plain, unlinked branding. */
  href?: string;
  onClick?: () => void;
  className?: string;
  /** Inverts the label for use on the ink bands, which are not token surfaces. */
  tone?: "default" | "on-ink";
}

/** Mark plus product name, the lockup used in every header and footer. */
export function Wordmark({
  href,
  onClick,
  className,
  tone = "default",
}: WordmarkProps) {
  const content = (
    <>
      <LogoMark />
      <span
        className={cn(
          "text-[15px] font-semibold tracking-tight",
          tone === "on-ink" ? "text-ink-foreground" : "text-foreground",
        )}
      >
        SupportMind
      </span>
    </>
  );

  const classes = cn(
    "flex w-fit items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    className,
  );

  if (!href) {
    return <span className={classes}>{content}</span>;
  }

  return (
    <Link href={href} onClick={onClick} className={classes}>
      {content}
    </Link>
  );
}
