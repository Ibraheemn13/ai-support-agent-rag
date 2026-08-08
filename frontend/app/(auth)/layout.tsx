import { Check } from "lucide-react";

import { Wordmark } from "@/components/common/logo";

const highlights = [
  "Answers drawn from documents you uploaded",
  "Every reply shows the passages behind it",
  "Separate workspaces for separate projects or teams",
];

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-dvh bg-surface lg:grid-cols-2">
      {/* Explanation panel; hidden on small screens so the form gets the space. */}
      <section className="on-ink hidden bg-ink px-12 py-14 text-ink-foreground lg:flex lg:flex-col lg:justify-between">
        <Wordmark href="/" tone="on-ink" />

        <div className="max-w-md pb-6">
          <h1 className="font-display text-[2.75rem] font-semibold leading-[1.08]">
            Turn your documents into an assistant that{" "}
            <span className="text-primary">cites its sources</span>.
          </h1>
          <p className="mt-5 text-base leading-7 text-ink-foreground/70">
            Upload the policies, FAQs, and notes you already have, then ask
            questions and get answers with clear sources.
          </p>

          <ul className="mt-8 space-y-3">
            {highlights.map((highlight) => (
              <li key={highlight} className="flex items-start gap-3 text-sm">
                <Check
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <span className="text-ink-foreground/90">{highlight}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-ink-foreground/50">
          Answers are grounded in your documents, not the open web.
        </p>
      </section>

      <section className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">{children}</div>
      </section>
    </main>
  );
}
