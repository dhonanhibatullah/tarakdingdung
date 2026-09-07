"use client";

import { CircleDollarSign, Menu } from "lucide-react";

import IconButton from "@/components/ui/icon-button";
import StatusBadge from "@/components/ui/status-badge";
import { APP_NAME } from "@/config/app";

interface AppBarProps {
  navigationOpen?: boolean;
  onNavigationToggle?: () => void;
}

export default function AppBar({
  navigationOpen = false,
  onNavigationToggle = () => undefined,
}: AppBarProps) {
  return (
    <header className="border-border bg-background/95 sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b px-4 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <IconButton
          aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navigationOpen}
          onClick={onNavigationToggle}
        >
          <Menu aria-hidden="true" className="size-5" />
        </IconButton>
        <div className="flex min-w-0 items-center gap-2">
          <CircleDollarSign
            aria-hidden="true"
            className="text-primary size-8 shrink-0"
          />
          <span className="font-display text-foreground hidden truncate text-lg tracking-wide sm:inline">
            {APP_NAME}
          </span>
        </div>
      </div>

      <StatusBadge variant="neutral">Engine idle</StatusBadge>
    </header>
  );
}
