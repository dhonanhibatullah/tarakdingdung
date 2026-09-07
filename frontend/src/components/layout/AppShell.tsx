"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { visibleNavigation } from "@/lib/navigation";
import type { UserResponse } from "@/lib/api/users";

import AppBar from "./AppBar";
import Sidebar from "./Sidebar";

interface AppShellProps {
  user: UserResponse;
  permissions: readonly string[];
  children: ReactNode;
}

export default function AppShell({
  user,
  permissions,
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const [navigationOpen, setNavigationOpen] = useState(true);
  const mainContentRef = useRef<HTMLDivElement>(null);
  const navigation = visibleNavigation(new Set(permissions));

  useEffect(() => {
    mainContentRef.current?.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="bg-background flex h-screen flex-col overflow-x-clip">
      <a
        href="#main-content"
        className="bg-primary text-surface focus-visible:ring-focus fixed top-2 left-4 z-50 -translate-y-20 rounded-xl px-4 py-2.5 text-sm font-semibold transition-transform focus-visible:translate-y-0 focus-visible:ring-2 focus-visible:outline-none"
      >
        Skip to main content
      </a>
      <AppBar
        userName={user.name}
        navigationOpen={navigationOpen}
        onNavigationToggle={() => setNavigationOpen((open) => !open)}
      />
      <div className="flex min-h-0 flex-1">
        <aside
          className={`border-border bg-surface/30 shrink-0 overflow-hidden border-r transition-[width] duration-200 ${
            navigationOpen ? "w-64" : "w-0 border-r-0"
          }`}
        >
          <div className="h-full w-64 overflow-y-auto">
            <Sidebar
              navigation={navigation}
              pathname={pathname}
              idPrefix="nav"
            />
          </div>
        </aside>
        <div
          ref={mainContentRef}
          id="main-content"
          tabIndex={-1}
          className="min-w-0 flex-1 overflow-y-auto focus:outline-none"
        >
          {children}
        </div>
      </div>
    </div>
  );
}
