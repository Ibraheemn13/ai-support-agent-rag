/**
 * WCAG contrast audit over the design tokens.
 *
 * Reads the values straight out of `app/globals.css` rather than keeping its
 * own copy, so the audit cannot drift from the stylesheet it is auditing. Run
 * it with `npm run check:contrast`.
 *
 * Thresholds are WCAG 2.1 AA: 4.5:1 for body text, 3:1 for large text and for
 * the boundary of a user interface component (1.4.11).
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "..", "app", "globals.css"), "utf8");

/** Pull the custom properties out of one top-level rule. */
function block(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = css.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`));
  if (!match) throw new Error(`no ${selector} block in globals.css`);
  return Object.fromEntries(
    [...match[1].matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(([, k, v]) => [
      k,
      v.trim(),
    ]),
  );
}

function luminance(hex) {
  const h = hex.replace("#", "");
  const channel = (c) =>
    c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  const [r, g, b] = [0, 2, 4].map((i) =>
    channel(parseInt(h.slice(i, i + 2), 16) / 255),
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
  const [lo, hi] = [luminance(a), luminance(b)].sort((x, y) => x - y);
  return (hi + 0.05) / (lo + 0.05);
}

/** [foreground token, background token, what it is, minimum ratio] */
const PAIRS = [
  ["--foreground", "--background", "body text on page", 4.5],
  ["--foreground", "--surface", "body text on card", 4.5],
  ["--foreground-muted", "--background", "muted text on page", 4.5],
  ["--foreground-muted", "--surface", "muted text on card", 4.5],
  ["--foreground-muted", "--surface-subtle", "muted text on tinted band", 4.5],
  ["--foreground-subtle", "--surface", "subtle text on card", 4.5],
  ["--foreground-subtle", "--background", "subtle text on page", 4.5],
  ["--primary", "--surface", "accent text on card", 4.5],
  ["--primary", "--background", "accent text on page", 4.5],
  ["--primary", "--surface-subtle", "accent eyebrow on tinted band", 4.5],
  ["--primary", "--primary-surface", "accent on its own tint", 4.5],
  ["--primary-foreground", "--primary", "primary button label", 4.5],
  ["--success", "--success-surface", "Ready badge", 4.5],
  ["--success-foreground", "--success", "completed step marker", 4.5],
  ["--warning", "--warning-surface", "Processing badge", 4.5],
  ["--danger", "--danger-surface", "Failed badge", 4.5],
  ["--info", "--info-surface", "Extracted badge", 4.5],
  ["--danger-foreground", "--danger", "destructive button label", 4.5],
  ["--ink-foreground", "--ink", "text on the ink band", 4.5],
  ["--input", "--surface", "form control border on card", 3],
  ["--input", "--background", "form control border on page", 3],
  ["--ring", "--background", "focus ring on page", 3],
];

/**
 * Inside `.on-ink` the band redefines the tokens its children read, so these
 * pairs have to be resolved against the band rather than against the page.
 */
const ON_INK_PAIRS = [
  ["--primary", "--ink", "accent text on the ink band", 4.5],
  ["--primary-foreground", "--primary", "primary button on the ink band", 4.5],
  ["--foreground-muted", "--ink", "muted text on the ink band", 4.5],
];

const light = block(":root");
const dark = { ...light, ...block(".dark") };
const onInk = block(".on-ink");

let failures = 0;

for (const [name, tokens] of [
  ["LIGHT", light],
  ["DARK", dark],
]) {
  console.log(`\n${name}\n${"-".repeat(62)}`);

  const checks = [
    ...PAIRS.map((pair) => [pair, tokens]),
    // The band keeps the theme's --ink but overrides everything drawn on it.
    ...ON_INK_PAIRS.map((pair) => [pair, { ...tokens, ...onInk }]),
  ];

  for (const [[fg, bg, label, floor], source] of checks) {
    const value = ratio(source[fg], source[bg]);
    const ok = value >= floor;
    if (!ok) failures += 1;
    const status = ok ? "ok  " : "FAIL";
    console.log(
      `${status} ${value.toFixed(2).padStart(5)}:1  (min ${floor})  ${label}`,
    );
  }
}

console.log(`\n${failures} failure${failures === 1 ? "" : "s"}`);
process.exit(failures ? 1 : 0);
