"use client";

import { LogOut, Menu, UserRound } from "lucide-react";

import { ThemeToggle } from "@/components/common/theme-toggle";
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { User } from "@/types/auth";
import type { Workspace } from "@/types/workspace";

interface TopBarProps {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onWorkspaceSelect: (workspaceId: string) => void;
  onCreateWorkspace?: () => void;
  user: User | null;
  onSignOut: () => void;
  onOpenNavigation: () => void;
  className?: string;
}

function displayName(user: User | null): string {
  return user?.full_name?.trim() || user?.email || "Account";
}

export function TopBar({
  workspaces,
  activeWorkspace,
  onWorkspaceSelect,
  onCreateWorkspace,
  user,
  onSignOut,
  onOpenNavigation,
  className,
}: TopBarProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border bg-surface px-4 sm:px-6",
        className,
      )}
    >
      <Button
        aria-label="Open navigation"
        className="-ml-2 lg:hidden"
        onClick={onOpenNavigation}
        size="icon"
        variant="ghost"
      >
        <Menu aria-hidden="true" />
      </Button>

      <WorkspaceSwitcher
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        onSelect={onWorkspaceSelect}
        onCreate={onCreateWorkspace}
      />

      <div className="flex-1" />

      <ThemeToggle />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            aria-label="Open account menu"
            className="max-w-[12rem] gap-2 px-2"
            variant="ghost"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-subtle text-foreground-muted">
              <UserRound aria-hidden="true" className="size-4" />
            </span>
            <span className="hidden min-w-0 truncate text-sm sm:block">
              {displayName(user)}
            </span>
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="normal-case tracking-normal">
            <span className="block truncate text-sm text-foreground">
              {displayName(user)}
            </span>
            {user?.email && user.full_name ? (
              <span className="mt-0.5 block truncate text-xs font-normal text-foreground-subtle">
                {user.email}
              </span>
            ) : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={onSignOut}>
            <LogOut aria-hidden="true" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
