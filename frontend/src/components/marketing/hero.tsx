import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { HeroDiagram } from "@/components/marketing/hero-diagram";
import { Container } from "@/components/marketing/section";
import { ProductPreview } from "@/components/marketing/product-preview";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-20">
      <Container>
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr] lg:gap-16">
          <div>
            {/* Steps down at lg, not up: that is where the hero becomes two
                columns and the headline loses half the width it had at sm. */}
            <h1 className="font-display text-[2.5rem] font-semibold leading-[1.06] text-foreground sm:text-5xl lg:text-[2.9rem] xl:text-[3.4rem]">
              Turn your documents into an assistant that{" "}
              <span className="text-primary">cites its sources</span>.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-foreground-muted">
              Upload the policies, FAQs, and notes you already have. Ask a
              question in plain language and get an answer with the passages it
              came from.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/register">
                  Build your assistant
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary">
                <a href="#how-it-works">See how it works</a>
              </Button>
            </div>

            <p className="mt-6 flex items-center gap-2.5 text-sm text-foreground-subtle">
              <span
                aria-hidden="true"
                className="size-1.5 shrink-0 rounded-full bg-primary"
              />
              Answers are grounded in your documents, not the open web.
            </p>
          </div>

          <HeroDiagram className="max-w-lg justify-self-center lg:max-w-none" />
        </div>

        {/* Supporting proof: the diagram states the claim, this shows it happening. */}
        <ProductPreview className="mx-auto mt-16 max-w-3xl" />
      </Container>
    </section>
  );
}
