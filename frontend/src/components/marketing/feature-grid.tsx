import {
  FileSearch,
  History,
  Layers,
  Quote,
  ShieldCheck,
  Wand2,
} from "lucide-react";

import { Section, SectionHeading } from "@/components/marketing/section";

const features = [
  {
    icon: FileSearch,
    title: "Document-based answers",
    body: "Replies are generated from the documents you uploaded, so the assistant stays inside what you actually published.",
  },
  {
    icon: Quote,
    title: "Sources from your knowledge",
    body: "Every answer lists the passages behind it, with the document each one came from.",
  },
  {
    icon: Layers,
    title: "Multi-workspace support",
    body: "Keep separate workspaces for different clients, products, or teams, each with its own knowledge spaces.",
  },
  {
    icon: History,
    title: "Conversation history",
    body: "Past chats are saved with their sources, so you can return to an answer and see what backed it.",
  },
  {
    icon: Wand2,
    title: "Simple document processing",
    body: "One action takes a file from uploaded to ready. Progress is visible the whole way through.",
  },
  {
    icon: ShieldCheck,
    title: "Workspace-scoped data",
    body: "Documents, chats, and search are scoped to the workspace that owns them, enforced by the API on every request.",
  },
];

export function FeatureGrid() {
  return (
    <Section id="features" muted>
      <SectionHeading
        eyebrow="Features"
        title="Built around one job: answering from your own content"
      />

      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ icon: Icon, title, body }) => (
          <div
            key={title}
            className="rounded-lg border border-border bg-surface p-5"
          >
            <span className="flex size-9 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-muted">
              <Icon aria-hidden="true" className="size-[18px]" />
            </span>
            <h3 className="mt-4 text-base font-semibold text-foreground">
              {title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-foreground-muted">
              {body}
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}
