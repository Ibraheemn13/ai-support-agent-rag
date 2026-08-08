import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

/**
 * Display face, used through the `.font-display` class on headings only.
 *
 * SOFT and WONK are requested explicitly because a variable font is subsetted
 * to the axes you ask for — without them the file ships with `wght` alone and
 * the `font-variation-settings` in globals.css would silently do nothing.
 */
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
});

export const metadata: Metadata = {
  title: {
    default: "SupportMind",
    template: "%s · SupportMind",
  },
  description:
    "Turn your documents into an AI assistant that answers from your own knowledge and cites its sources.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    /*
     * next-themes writes the theme class onto <html> from a blocking script
     * before first paint, which is what prevents the flash of the wrong theme.
     * That makes the server-rendered markup differ from the client's by
     * construction, so the warning has to be suppressed here — it is the
     * documented setup, not a papered-over mismatch. It applies to this element
     * only, not to its subtree.
     */
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
