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
  proxy.ts               Next 16 middleware: session gate + edge token refresh
  app/
    layout.tsx            root: fonts (Inter + Poppins), metadata, <ToastProvider>
    page.tsx              redirects / -> /dashboard or /login by session
    forbidden.tsx         the 403 page (authInterrupts)
    globals.css           Tailwind import + the @theme design tokens
    login/               login page + LoginForm + SignedOutNotice + _lib/actions
    auth/invalid-session/  route handler: clears cookies, 307 -> /login
    (app)/
      layout.tsx          requireSessionContext() -> <AppShell user permissions>
      dashboard/          the overview page + its _components
      strategies/         page + loading + error + _components/ + _lib/ (fully wired)
      backtests/ … admin/access-control/   one page.tsx each (placeholders)
  components/
    layout/   AppShell, AppBar, Sidebar, SidebarGroup, is-current-path, LogoutButton, AccessDenied
    ui/       card, page-header, status-badge, icon-button, states, placeholder-page,
              button, input, label, select, toast, toast-provider
    collection/  FilterBar, Pagination, ResourceCard
  hooks/     use-toast, use-action-feedback
  lib/
    api/       client (apiFetch + ApiError), auth, types, version, profile,
               users, permissions, roles, strategies — server-only
    session/   cookies, jwt (decodeJwtExpiry), session (getSession,
               getSessionContext, requireSessionContext, requireAnyPermission)
    actions/   session-actions (logoutAction)
    forms/     action-state, parse (formText, formBool, parseJsonObject)
    navigation.ts       isProtectedRoute, canVisitRoute, visibleNavigation
    permissions.ts      hasPermission, canAccessAny
    query.ts / collection-query.ts   search-param parsing + page query
  config/
    app.ts         APP_NAME, APP_VERSION
    navigation.ts  NAVIGATION (each page's requiredAny perms) + PUBLIC_ROUTES
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

## Auth & sessions

Ported from `nusapala-things/frontend`. Every route except `PUBLIC_ROUTES`
(`/`, `/login`, `/auth/invalid-session`) requires a signed-in session.

- **Login:** `POST /api/v1/auth/login` returns `{ user, role, permissions,
  access_token, refresh_token }`. `lib/api/auth.ts:persistSession` writes both
  tokens as httpOnly cookies (`trdd_access_token` / `trdd_refresh_token`),
  `secure` from `TRDD_FE_COOKIE_SECURE`, `expires` decoded from the JWT `exp`.
- **`src/proxy.ts`** (Next 16 middleware — the file is `proxy.ts`, exporting
  `proxy` + `config`, not `middleware.ts`): redirects protected routes to
  `/login` with no valid session; when the access token is expired/near, calls
  the backend refresh at the edge and rewrites the cookies; bounces `/login`
  to `/dashboard` when already signed in.
- **Server side:** `requireSessionContext()` (in `(app)/layout.tsx`) redirects
  to `/login`; `requireAnyPermission([...])` calls `forbidden()` (needs
  `experimental.authInterrupts` in `next.config.ts`) when the token's
  `permissions` claim lacks all of them. `AppShell` gets `user` + `permissions`
  and `visibleNavigation` hides links the session can't open.
- **Mutations** are server actions in `_lib/actions.ts` files: re-check the
  permission, call `lib/api/*`, `revalidatePath()`, return an `ActionResult`
  the client surfaces via `useActionFeedback` -> toast.

Backend contract: all `/api/v1/trading/*` need `Authorization: Bearer <jwt>`;
`apiFetch` attaches it from the cookie. Envelopes: `PageDataResponse<T>`,
`IdResponse`, `ErrorResponse` (`{ error, message }`) — see `lib/api/types.ts`.

## Data

Every route except the **dashboard** (still static sample figures behind a
"connect the engine API" note) is wired to the backend:

| Route | Reads | Writes |
| --- | --- | --- |
| `/strategies` | list + filters + pagination | create / enable-disable / delete / dry-run |
| `/backtests` | list + strategy filter + pagination | run backtest |
| `/validations` | look up a run by id | run walk-forward (redirects to `?id=`) — no list endpoint on the backend |
| `/portfolio` | current holdings, risk state, equity curve (`?days=`) | — |
| `/market-data` | candle coverage for a symbol/interval/window (filter form) | — |
| `/admin/users` | list + search + role filter + pagination | create / edit / reset password / delete |
| `/admin/access-control` | roles + permissions tabs (`?tab=`) | role & permission CRUD, set-default, per-role permission matrix |

Each follows the same shape: `page.tsx` gated by `requireAnyPermission`,
`lib/api/<resource>.ts` for the calls, `_lib/actions.ts` (`"use server"`) for
mutations returning an `ActionResult` (`lib/forms/result.ts`), `_components/`
for the view. Dialogs use `useDialogForm` + `<Modal>`; list pages reuse
`collection/{FilterBar,Pagination,ResourceCard}`; `error.tsx` is a thin
`<RouteError>`. Shared value formatting lives in `lib/format.ts`, window math
in `lib/time-window.ts`.

`lib/forms/result.ts` is deliberately import-free (client components pull
`INITIAL` from it) — its `fail()` duck-types `ApiError` rather than importing
the server-only api client.

## Environment

`TRDD_FE_`-prefixed, server-side only (no `NEXT_PUBLIC_`). See `.env.example`:
`TRDD_FE_API_BASE_URL`, `TRDD_FE_COOKIE_SECURE` (httpOnly session cookie
`secure` flag — keep `false` on local http), `TRDD_FE_HTTP_PORT` /
`TRDD_FE_BIND_HOST` (compose publish only). `cp .env.example .env` before
running.

## Running

- **Dev:** `pnpm install && pnpm dev` → http://localhost:3000
- **Check:** `pnpm lint`, `pnpm typecheck`, `pnpm build`
- **Docker:** `docker compose up --build` — multi-stage build of the Next
  `standalone` output, unprivileged runtime, healthcheck on `/login`. The
  container always serves on 3000; `TRDD_FE_HTTP_PORT` maps the host side,
  `TRDD_FE_BIND_HOST` the interface.
