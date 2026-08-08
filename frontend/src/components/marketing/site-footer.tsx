import Link from "next/link";

import { Wordmark } from "@/components/common/logo";
import { Container } from "@/components/marketing/section";

const footerLinks = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Features", href: "#features" },
  { label: "Use cases", href: "#use-cases" },
];

export function SiteFooter() {
  return (
    <footer className="bg-surface py-12">
      <Container>
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <Wordmark href="/" />
            <p className="mt-3 text-sm leading-6 text-foreground-muted">
              An AI assistant that answers from your own documents and shows its
              sources.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-col gap-2.5">
            {footerLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-foreground-muted transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/login"
              className="text-sm text-foreground-muted transition-colors hover:text-foreground"
            >
              Sign in
            </Link>
          </nav>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-foreground-subtle">
            A portfolio project demonstrating retrieval-augmented generation
            over multi-tenant document storage.
          </p>
          {/* One of two places on the site allowed to have a voice. */}
          <p className="flex items-center gap-2 text-xs text-foreground-subtle">
            <span
              aria-hidden="true"
              className="size-1.5 shrink-0 rounded-full bg-success"
            />
            All systems answering — and still refusing to make anything up.
          </p>
        </div>
      </Container>
    </footer>
  );
}
