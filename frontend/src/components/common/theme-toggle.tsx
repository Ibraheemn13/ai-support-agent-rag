"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useIsHydrated } from "@/hooks/use-is-hydrated";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

/**
 * Three choices rather than a binary switch.
 *
 * A two-state toggle cannot express "follow the system", so the moment someone
 * touches it they are opted out of their machine's own light/dark schedule with
 * no way back. The third option is the way back.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme();

  // The server cannot know the stored preference, so the first client render
  // has to match the server's guess or React reports a mismatch. This is the
  // same hydration boundary the session reads across, so it uses the same hook
  // rather than a second mount flag of its own.
  const hydrated = useIsHydrated();

  const Icon = hydrated && resolvedTheme === "dark" ? Moon : Sun;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          aria-label="Change theme"
          className={cn("text-foreground-muted", className)}
          size="icon"
          variant="ghost"
        >
          <Icon aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="min-w-36">
        <DropdownMenuRadioGroup
          value={hydrated ? theme : undefined}
          onValueChange={setTheme}
        >
          {OPTIONS.map(({ value, label, icon: OptionIcon }) => (
            <DropdownMenuRadioItem key={value} value={value} className="gap-2">
              <OptionIcon aria-hidden="true" className="size-4" />
              {label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
