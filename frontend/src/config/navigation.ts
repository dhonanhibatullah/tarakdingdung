export interface NavPage {
  href: string;
  label: string;
}

export interface NavGroup {
  label: string;
  pages: readonly NavPage[];
}

export const NAVIGATION: readonly NavGroup[] = [
  {
    label: "Overview",
    pages: [{ href: "/dashboard", label: "Overview" }],
  },
  {
    label: "Trading",
    pages: [
      { href: "/strategies", label: "Strategies" },
      { href: "/backtests", label: "Backtests" },
      { href: "/validations", label: "Validations" },
    ],
  },
  {
    label: "Markets",
    pages: [
      { href: "/portfolio", label: "Portfolio" },
      { href: "/market-data", label: "Market Data" },
    ],
  },
  {
    label: "Administration",
    pages: [
      { href: "/admin/users", label: "Users" },
      { href: "/admin/access-control", label: "Access Control" },
    ],
  },
];
