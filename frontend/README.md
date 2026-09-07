# tarakdingdung frontend

Operator console for the tarakdingdung trading engine — strategies, backtests,
validations, portfolio, and market-data coverage. Next.js 16 (App Router),
React 19, Tailwind v4.

The shell and UI primitives are ported from `nusapala-things/frontend` so the
two consoles share one look; here the accent is green and the navigation is the
trading domain.

## Prerequisites

- Node 22+
- pnpm 12 (`corepack enable` picks up the pinned version)

## Develop

```bash
pnpm install
cp .env.example .env      # adjust TRDD_FE_API_BASE_URL if the backend isn't on :8888
pnpm dev
```

Open http://localhost:3000 — `/` redirects to `/dashboard`.

Checks: `pnpm lint`, `pnpm typecheck`, `pnpm build`.

## Configuration

All variables use the `TRDD_FE_` prefix and are read server-side only. See
`.env.example`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `TRDD_FE_API_BASE_URL` | Base URL of the backend API | `http://127.0.0.1:8888` |
| `TRDD_FE_COOKIE_SECURE` | Send the session cookie only over HTTPS | `false` |
| `TRDD_FE_HTTP_PORT` | Host port docker-compose publishes on | `3000` |

## Docker

```bash
cp .env.example .env      # optional; compose runs without it
docker compose up --build
```

Multi-stage build of the Next `standalone` output, run as an unprivileged user
with a healthcheck on `/dashboard`. The container listens on 3000;
`TRDD_FE_HTTP_PORT` maps the host side (`127.0.0.1:${TRDD_FE_HTTP_PORT}:3000`).

## Structure

See `AGENTS.md` for the directory map, the design-token system, and how to add a
navigation entry.

## Status

No API client or auth yet: the dashboard shows sample figures and the other
routes are placeholders. `src/config/env.ts` already reads the backend URL for
when data fetching is wired in.
