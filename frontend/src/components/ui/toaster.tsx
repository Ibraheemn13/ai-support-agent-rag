"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  const { resolvedTheme } = useTheme();

  return (
    <Sonner
      closeButton
      richColors
      // Sonner paints its own surfaces, so it has to be told which theme it is
      // in. Left on its default it renders light toasts over a dark app.
      theme={resolvedTheme === "dark" ? "dark" : "light"}
      position="top-right"
      duration={4_000}
      // Sonner's own mobile rule sets width:100% while also applying left and
      // right offsets, so the container ends up wider than the screen. Its
      // stylesheet is injected after ours, so the override has to be important
      // to win.
      className="max-sm:!inset-x-4 max-sm:!w-auto"
      toastOptions={{
        classNames: {
          toast: "border border-border bg-surface text-foreground shadow-lg",
          description: "text-foreground-muted",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-surface-hover text-foreground-muted",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
