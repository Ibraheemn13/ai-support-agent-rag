import { cn } from "@/lib/utils";

/** Shared horizontal gutter and max width for every marketing section. */
export function Container({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-6xl px-5 sm:px-8", className)}>
      {children}
    </div>
  );
}

interface SectionProps {
  children: React.ReactNode;
  id?: string;
  /** Tints the band so adjacent sections stay visually separated without rules. */
  muted?: boolean;
  className?: string;
}

export function Section({ children, id, muted, className }: SectionProps) {
  return (
    <section
      id={id}
      className={cn(
        "scroll-mt-16 py-16 sm:py-24",
        muted && "bg-surface-subtle",
        className,
      )}
    >
      <Container>{children}</Container>
    </section>
  );
}

interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  description?: string;
  /** Centred headings suit full-width bands; left-aligned suits content grids. */
  align?: "left" | "center";
  className?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "max-w-2xl",
        align === "center" && "mx-auto text-center",
        className,
      )}
    >
      {eyebrow ? (
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-primary">
          {eyebrow}
        </p>
      ) : null}
      <h2 className="font-display text-3xl font-semibold text-foreground sm:text-[2.5rem] sm:leading-[1.12]">
        {title}
      </h2>
      {description ? (
        <p className="mt-4 text-base leading-7 text-foreground-muted">
          {description}
        </p>
      ) : null}
    </div>
  );
}
