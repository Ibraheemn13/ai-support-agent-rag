"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  FileText,
  LayoutDashboard,
  MessagesSquare,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { Wordmark } from "@/components/common/logo";
import { cn } from "@/lib/utils";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Renders the item as unavailable. Used for areas not built yet. */
  comingSoon?: boolean;
  match?: (pathname: string) => boolean;
}

/** Labels and routes both use product language. */
export const navItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    match: (pathname) => pathname === "/dashboard",
  },
  {
    label: "Knowledge",
    href: "/dashboard/knowledge",
    icon: BookOpen,
  },
  {
    label: "Documents",
    href: "/dashboard/documents",
    icon: FileText,
  },
  {
    label: "Ask AI",
    href: "/dashboard/chat",
    icon: Sparkles,
  },
  {
    label: "Chat threads",
    href: "/dashboard/conversations",
    icon: MessagesSquare,
  },
  {
    label: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
  },
];

export function ProductMark({ className }: { className?: string }) {
  return (
    <Wordmark
      href="/dashboard"
      className={cn("h-16 rounded-none px-5", className)}
    />
  );
}

interface SidebarProps {
  items?: NavItem[];
  /** Called after navigating, so the mobile drawer can close itself. */
  onNavigate?: () => void;
  className?: string;
}

export function Sidebar({
  items = navItems,
  onNavigate,
  className,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main"
      className={cn("flex flex-col gap-0.5 px-3", className)}
    >
      {items.map((item) => {
        const Icon = item.icon;

        if (item.comingSoon) {
          return (
            <span
              key={item.href}
              aria-disabled="true"
              className="flex h-9 cursor-not-allowed items-center gap-3 rounded-md px-3 text-sm font-medium text-foreground-subtle/70"
            >
              <Icon aria-hidden="true" className="size-[18px]" />
              <span>{item.label}</span>
              <span className="ml-auto text-[10px] font-medium uppercase tracking-wide">
                Soon
              </span>
            </span>
          );
        }

        const isActive = item.match
          ? item.match(pathname)
          : pathname === item.href || pathname.startsWith(`${item.href}/`);

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-3 rounded-md px-3 text-sm font-medium text-foreground-muted transition-colors",
              "hover:bg-surface-hover hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              // Accent, not just a darker chip: where you are is worth colour.
              isActive && "bg-primary-surface text-primary",
            )}
          >
            <Icon aria-hidden="true" className="size-[18px]" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
