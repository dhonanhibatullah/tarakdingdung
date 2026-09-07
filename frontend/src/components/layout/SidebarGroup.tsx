import Link from "next/link";
import {
  ChartCandlestick,
  FlaskConical,
  LayoutDashboard,
  Radio,
  Shield,
  ShieldCheck,
  Users,
  Wallet,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import type { NavGroup } from "@/config/navigation";

import { isCurrentPath } from "./is-current-path";

const NAVIGATION_ICONS: Readonly<Record<string, LucideIcon>> = {
  "/dashboard": LayoutDashboard,
  "/strategies": Workflow,
  "/backtests": FlaskConical,
  "/validations": ShieldCheck,
  "/portfolio": Wallet,
  "/market-data": ChartCandlestick,
  "/admin/users": Users,
  "/admin/access-control": Shield,
};

interface SidebarGroupProps {
  group: NavGroup;
  pathname: string;
  idPrefix: string;
  onNavigate?: () => void;
}

export default function SidebarGroup({
  group,
  pathname,
  idPrefix,
  onNavigate,
}: SidebarGroupProps) {
  const headingId = `${idPrefix}-navigation-${group.label
    .toLowerCase()
    .replaceAll(" ", "-")}`;

  return (
    <section aria-labelledby={headingId}>
      <h2
        id={headingId}
        className="text-muted-foreground px-3 text-xs font-semibold tracking-wider uppercase"
      >
        {group.label}
      </h2>
      <ul className="mt-2 space-y-1">
        {group.pages.map((item) => {
          const Icon = NAVIGATION_ICONS[item.href] ?? Radio;
          const current = isCurrentPath(pathname, item.href);

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={current ? "page" : undefined}
                onClick={onNavigate}
                className={`focus-visible:ring-focus flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none ${
                  current
                    ? "bg-highlight/55 text-primary"
                    : "text-foreground/75 hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon aria-hidden="true" className="size-5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
