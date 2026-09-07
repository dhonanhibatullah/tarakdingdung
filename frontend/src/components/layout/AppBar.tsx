"use client";

import { CircleDollarSign, LogOut, Menu, UserRound } from "lucide-react";

import IconButton from "@/components/ui/icon-button";
import { APP_NAME } from "@/config/app";
import { logoutAction } from "@/lib/actions/session-actions";

interface AppBarProps {
  userName: string;
  navigationOpen?: boolean;
  onNavigationToggle?: () => void;
}

export default function AppBar({
  userName,
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

      <div className="flex min-w-0 items-center gap-2">
        <span className="bg-surface text-primary flex size-9 shrink-0 items-center justify-center rounded-full">
          <UserRound aria-hidden="true" className="size-5" />
        </span>
        <span className="max-w-32 truncate text-sm font-semibold sm:max-w-48">
          {userName}
        </span>
        <form action={logoutAction}>
          <IconButton type="submit" aria-label="Log out">
            <LogOut aria-hidden="true" className="size-5" />
          </IconButton>
        </form>
      </div>
    </header>
  );
}
