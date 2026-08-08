import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/marketing/section";
import { Button } from "@/components/ui/button";

export function CtaSection() {
  return (
    /*
     * Ink rather than the accent. A full-bleed terracotta band would be the
     * largest single area of colour on the page, which would make the accent
     * scenery instead of a signal — and it would leave the primary button with
     * nothing to stand out against.
     */
    <section className="border-y border-border bg-ink py-16 sm:py-20">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-semibold text-ink-foreground sm:text-[2.5rem] sm:leading-[1.12]">
            Point it at your documents and ask a question.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-ink-foreground/70">
            Create a workspace, add a document, and see a cited answer in a few
            minutes.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/register">
                Build your assistant
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="ghost"
              className="text-ink-foreground hover:bg-ink-foreground/10 hover:text-ink-foreground"
            >
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
