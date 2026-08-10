import { cn } from "@/lib/utils";

/**
 * The hero illustration: several documents converging into one cited answer.
 *
 * It has to carry the product before anyone reads the headline, so it is built
 * as a single chain in the accent colour — the marked document, the line out of
 * it, the node, the highlighted sentence, and the source pill are all
 * terracotta, and everything else is neutral. Following the colour *is*
 * following the claim: this passage produced this answer, and here is the file
 * it came from.
 *
 * The filename is the only real text. Left fully abstract the drawing reads as
 * generic dataflow; one concrete document name makes it unmistakably "an answer
 * that cites a source" without needing a caption.
 *
 * Every colour is a token, so it repaints for dark mode rather than needing a
 * second asset.
 */
export function HeroDiagram({ className }: { className?: string }) {
  return (
    <svg
      className={cn("w-full", className)}
      viewBox="0 0 460 300"
      role="img"
      aria-label="Three documents feeding into a single answer, which cites the document it came from"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Documents. The middle one is the source the answer will cite. */}
      <g>
        <rect
          className="fill-surface stroke-border-strong"
          x="8"
          y="44"
          width="76"
          height="58"
          rx="6"
        />
        <g className="fill-border-strong">
          <rect x="20" y="58" width="46" height="4.5" rx="2.25" />
          <rect x="20" y="69" width="52" height="4.5" rx="2.25" />
          <rect x="20" y="80" width="34" height="4.5" rx="2.25" />
        </g>

        <rect
          className="fill-surface stroke-primary"
          x="8"
          y="120"
          width="76"
          height="58"
          rx="6"
        />
        <g className="fill-primary">
          <rect x="20" y="134" width="46" height="4.5" rx="2.25" />
          <rect x="20" y="145" width="52" height="4.5" rx="2.25" opacity="0.55" />
          <rect x="20" y="156" width="34" height="4.5" rx="2.25" opacity="0.35" />
        </g>

        <rect
          className="fill-surface stroke-border-strong"
          x="8"
          y="196"
          width="76"
          height="58"
          rx="6"
        />
        <g className="fill-border-strong">
          <rect x="20" y="210" width="46" height="4.5" rx="2.25" />
          <rect x="20" y="221" width="52" height="4.5" rx="2.25" />
          <rect x="20" y="232" width="34" height="4.5" rx="2.25" />
        </g>
      </g>

      {/* Convergence into the assistant */}
      <path
        className="stroke-border-strong"
        d="M84 73 C 126 73, 126 149, 158 149"
        fill="none"
        strokeWidth="1.6"
      />
      <path
        className="stroke-primary"
        d="M84 149 H 158"
        fill="none"
        strokeWidth="1.9"
      />
      <path
        className="stroke-border-strong"
        d="M84 225 C 126 225, 126 149, 158 149"
        fill="none"
        strokeWidth="1.6"
      />
      <rect
        className="fill-primary"
        x="158"
        y="135"
        width="28"
        height="28"
        rx="8"
      />
      <circle className="fill-primary-foreground" cx="172" cy="149" r="4.6" />
      <path
        className="stroke-primary"
        d="M186 149 H 218"
        fill="none"
        strokeWidth="1.9"
      />

      {/* The answer, with the sentence it drew from the marked document */}
      <rect
        className="fill-surface stroke-border-strong"
        x="218"
        y="62"
        width="234"
        height="140"
        rx="10"
      />
      <g className="fill-foreground-muted">
        <rect x="238" y="86" width="194" height="5.5" rx="2.75" />
        <rect x="238" y="99" width="176" height="5.5" rx="2.75" />
      </g>
      <rect
        className="fill-primary-surface"
        x="233"
        y="112"
        width="160"
        height="17"
        rx="3"
      />
      <rect
        className="fill-primary"
        x="238"
        y="118.5"
        width="150"
        height="5.5"
        rx="2.75"
      />
      <rect
        className="fill-foreground-muted"
        x="238"
        y="138"
        width="130"
        height="5.5"
        rx="2.75"
      />

      {/* The citation */}
      <rect
        className="fill-primary-surface stroke-primary-border"
        x="233"
        y="158"
        width="170"
        height="24"
        rx="12"
      />
      <circle className="fill-primary" cx="248" cy="170" r="3.4" />
      <text
        className="fill-primary text-[11px] font-medium"
        x="258"
        y="174"
      >
        Refund Policy.pdf
      </text>
      <path
        className="stroke-primary"
        d="M231 170 C 204 170, 198 156, 189 152"
        fill="none"
        strokeWidth="1.4"
        strokeDasharray="3 4"
        opacity="0.6"
      />
    </svg>
  );
}
