import { Section, SectionHeading } from "@/components/marketing/section";

const steps = [
  {
    title: "Create your workspace",
    body: "Set up a workspace — for yourself or for your whole team — then add a knowledge space for each area you want the assistant to cover.",
  },
  {
    title: "Upload your documents",
    body: "Drop in PDFs, FAQs, policies, or product docs. One action prepares them for chat; you never touch a processing pipeline.",
  },
  {
    title: "Ask questions and get cited answers",
    body: "Ask in plain language. Every answer arrives with the source passages it came from, so you can check the reasoning.",
  },
];

export function HowItWorks() {
  return (
    <Section id="how-it-works">
      <SectionHeading
        eyebrow="How it works"
        title="Three steps from documents to answers"
        description="No embedding configuration, no pipeline babysitting, and no vocabulary you need a machine learning background to follow."
      />

      <ol className="mt-12 grid gap-8 sm:grid-cols-3">
        {steps.map((step, index) => (
          <li key={step.title} className="relative">
            <span className="flex size-8 items-center justify-center rounded-full border border-primary-border bg-primary-surface text-sm font-semibold text-primary">
              {index + 1}
            </span>
            <h3 className="mt-4 text-base font-semibold text-foreground">
              {step.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-foreground-muted">
              {step.body}
            </p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
