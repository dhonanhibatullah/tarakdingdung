<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# tarakdingdung frontend

The operator console for the trading engine: strategies, backtests, validations,
portfolio, market-data coverage, and admin. Next 16 (App Router, Turbopack),
React 19, Tailwind v4, `lucide-react` for icons. `pnpm` only.

## Where it came from

The shell, the token system, and the `ui/` primitives are ported almost
verbatim from `../nusapala-things/frontend` so the two consoles feel like one
product. When extending, copy that repo's pattern rather than inventing a new
one; the only deliberate divergences here are the green accent, the coin logo,
and the trading-domain navigation.

## Layout

```
src/
  app/
    layout.tsx            root: fonts (Inter + Poppins), metadata
    page.tsx              redirects / -> /dashboard
    globals.css           Tailwind import + the @theme design tokens
    (app)/
      layout.tsx          wraps everything in <AppShell>
      dashboard/          the overview page + its _components
      strategies/ … admin/access-control/   one page.tsx each (placeholders)
  components/
    layout/   AppShell, AppBar, Sidebar, SidebarGroup, is-current-path
    ui/       card, page-header, status-badge, icon-button, states, placeholder-page
  config/
    app.ts         APP_NAME, APP_VERSION
    navigation.ts  NAVIGATION: the sidebar groups and their routes
    env.ts         TRDD_FE_* reads (API_BASE_URL, COOKIE_SECURE)
    index.ts       re-export
```

`@/*` resolves to `src/*` (tsconfig `paths`).

## Design tokens

`globals.css` defines CSS custom properties on `:root`, remaps them into
Tailwind via `@theme inline`, and overrides them under
`@media (prefers-color-scheme: dark)`. Components reference the semantic names
(`text-primary`, `bg-surface`, `bg-highlight/55`, `border-border`,
`focus-visible:ring-focus`, …), never raw hex. To restyle, edit the token
values in one place; the accent here is green (`--primary` `#15803d` light /
`#22c55e` dark). `font-display` = Poppins; body = Inter.

## Navigation

`src/config/navigation.ts` is the single source. Each `NavPage` needs a route
with a matching `page.tsx` under `src/app/(app)/`, and an icon entry in
`SidebarGroup.tsx`'s `NAVIGATION_ICONS` map (falls back to `Radio`).

## Data

There is no API client, session, or auth layer yet. The dashboard renders
static sample figures behind a visible "connect the engine API" note, and every
non-dashboard route is an honest placeholder. `config/env.ts` already reads the
backend URL and cookie flag for when fetching is wired in — mirror
nusapala-things' `lib/api/` + `lib/session/` when you add it.

## Environment

`TRDD_FE_`-prefixed, server-side only (no `NEXT_PUBLIC_`). See `.env.example`:
`TRDD_FE_API_BASE_URL`, `TRDD_FE_COOKIE_SECURE`, `TRDD_FE_HTTP_PORT` (compose
publish port only). `cp .env.example .env` before running.

## Running

- **Dev:** `pnpm install && pnpm dev` → http://localhost:3000
- **Check:** `pnpm lint`, `pnpm typecheck`, `pnpm build`
- **Docker:** `docker compose up --build` — multi-stage build of the Next
  `standalone` output, unprivileged runtime, healthcheck on `/dashboard`. The
  container always serves on 3000; `TRDD_FE_HTTP_PORT` maps the host side.
