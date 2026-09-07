import type { PermissionName } from "@/lib/permissions";

export interface NavPage {
  href: string;
  label: string;
  /** Omitted = any signed-in user may visit; otherwise any one suffices. */
  requiredAny?: readonly PermissionName[];
}

export interface NavGroup {
  label: string;
  pages: readonly NavPage[];
}

/** Routes that don't require a session. Everything else is protected. */
export const PUBLIC_ROUTES: readonly string[] = [
  "/",
  "/login",
  "/auth/invalid-session",
];

export const NAVIGATION: readonly NavGroup[] = [
  {
    label: "Overview",
    pages: [{ href: "/dashboard", label: "Overview" }],
  },
  {
    label: "Trading",
    pages: [
      { href: "/strategies", label: "Strategies", requiredAny: ["strategy:get"] },
      { href: "/backtests", label: "Backtests", requiredAny: ["backtest:get"] },
      {
        href: "/validations",
        label: "Validations",
        requiredAny: ["backtest:get"],
      },
    ],
  },
  {
    label: "Markets",
    pages: [
      {
        href: "/portfolio",
        label: "Portfolio",
        requiredAny: ["portfolio:get"],
      },
      {
        href: "/market-data",
        label: "Market Data",
        requiredAny: ["market_data:get"],
      },
    ],
  },
  {
    label: "Administration",
    pages: [
      { href: "/admin/users", label: "Users", requiredAny: ["user:get"] },
      {
        href: "/admin/access-control",
        label: "Access Control",
        requiredAny: ["role:get", "permission:get", "role_permission:get"],
      },
    ],
  },
];
