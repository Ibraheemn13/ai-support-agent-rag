import { Section, SectionHeading } from "@/components/marketing/section";

const useCases = [
  {
    title: "Customer support",
    body: "Give yourself, or a whole team of agents, a fast way to check refund windows, shipping rules, and account policies without opening four documents.",
    example: "“How long does a customer have to return an opened item?”",
  },
  {
    title: "Product documentation",
    body: "Let the team ask the docs directly instead of scrolling through release notes and configuration guides.",
    example: "“Which plans include the audit log?”",
  },
  {
    title: "Internal team knowledge",
    body: "Turn onboarding guides and process docs into something a new hire can question in plain language.",
    example: "“What is the approval process for a new vendor?”",
  },
  {
    title: "Policies and FAQs",
    body: "Answer the same client question the same way every time, straight from the terms you actually published.",
    example: "“What are my revision limits on a fixed-price project?”",
  },
];

export function UseCases() {
  return (
    <Section id="use-cases">
      <SectionHeading
        eyebrow="Use cases"
        title="Wherever the answer is already written down"
      />

      <div className="mt-12 grid gap-6 sm:grid-cols-2">
        {useCases.map((useCase) => (
          <div
            key={useCase.title}
            className="rounded-lg border border-border bg-surface p-6"
          >
            <h3 className="text-base font-semibold text-foreground">
              {useCase.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-foreground-muted">
              {useCase.body}
            </p>
            <p className="mt-4 border-l-2 border-border pl-3 text-sm italic leading-6 text-foreground-subtle">
              {useCase.example}
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}
