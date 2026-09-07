# 002 — `docker compose up` produces a permanently-unhealthy, unreachable container

- **Severity:** high
- **Status:** done (fixed 2026-09-07)
- **Detected:** 2026-09-07
- **Area:** `backend/docker-compose.yml`, `backend/docker/entrypoint.sh`, `backend/Dockerfile`

## Resolution

Adopted the "container always binds 8080 internally; `TRDD_BE_HTTP_PORT`
selects only the host-published port" convention.

- `docker-compose.yml` `x-backend.environment:` now sets
  `TRDD_BE_HTTP_PORT: "8080"` (alongside the existing `TRDD_BE_HTTP_HOST:
  0.0.0.0`), so `env_file`'s value is overridden for the process. uvicorn, the
  `ports:` right side, the compose healthcheck and `EXPOSE` now all agree on
  8080 inside the container. `ports: "127.0.0.1:${TRDD_BE_HTTP_PORT:-8080}:8080"`
  is unchanged — its left side still reads `TRDD_BE_HTTP_PORT` from the shell /
  `.env`, so the host-published port stays configurable.
- `.env.example` gains a comment noting that under compose `TRDD_BE_HTTP_PORT`
  is the host-published port only.

**Verified:** `docker compose up -d backend` → `healthy` in ~9s; host
`127.0.0.1:18888` (the `.env` value) → container `:8080` → reachable
(`GET /api/version` → `v0.1.0-dev.1`). `docker compose run --rm seeder` also
works.

---

## Original analysis

## Symptom

`docker compose up -d backend` with the repo's own `.env` (or the values in
`.env.example`) yields:

- container status stuck at `health: starting` → `unhealthy`, never `healthy`
- `curl http://127.0.0.1:<published>/api/version` from the host → `Connection reset by peer`
- healthcheck log: `curl: (7) Failed to connect to 127.0.0.1 port 8080 ... Could not connect to server` (`ExitCode: 7`, repeating)

The application itself starts fine — migrations run, uvicorn comes up — it is
just bound to the wrong port relative to what compose and the healthcheck
expect.

## Root cause — three places disagree about the in-container port

`entrypoint.sh` starts uvicorn on `--port "${TRDD_BE_HTTP_PORT:-8080}"`. The
`.env` is loaded via `env_file`, and it sets:

```
TRDD_BE_HTTP_PORT=18888        # .env  (real)
TRDD_BE_HTTP_PORT=8888         # .env.example (shipped default)
```

So uvicorn binds **18888** (or 8888) *inside the container*. But:

| Location | Assumes container port |
|----------|------------------------|
| `docker-compose.yml` `ports:` → `"127.0.0.1:${TRDD_BE_HTTP_PORT:-8080}:8080"` | **8080** (right side hardcoded) |
| `docker-compose.yml` `healthcheck.test` → `curl ... http://127.0.0.1:8080/api/version` | **8080** (hardcoded) |
| `Dockerfile` `EXPOSE 8080` | 8080 |
| `Dockerfile` `HEALTHCHECK` → `...:${TRDD_BE_HTTP_PORT:-8080}/...` | follows the env var (this one is actually correct) |

Net effect: host `:18888` → container `:8080` (nothing listening) → published
port dead; healthcheck curls container `:8080` → dead → unhealthy forever.
It only works when `TRDD_BE_HTTP_PORT` is unset or exactly `8080`.

The compose `environment:` block already forces `TRDD_BE_HTTP_HOST: 0.0.0.0`
for the same "bind inside the container, not on whatever the host uses"
reason — it just doesn't do the same for the port.

## Workaround (used during verification)

```bash
docker run -d --env-file .env -e TRDD_BE_HTTP_PORT=8080 -e TRDD_BE_HTTP_HOST=0.0.0.0 \
  --add-host host.docker.internal:host-gateway -p 127.0.0.1:18888:8080 \
  tarakdingdung-backend:latest serve
```

## Suggested direction

Pick one convention and make all four places obey it. Simplest: the container
**always** binds 8080 internally; `TRDD_BE_HTTP_PORT` controls only the
host-published port.

- `docker-compose.yml` `environment:` — add `TRDD_BE_HTTP_PORT: 8080` (mirrors
  the existing `TRDD_BE_HTTP_HOST` override).
- `docker-compose.yml` `ports:` — `"127.0.0.1:${TRDD_BE_HTTP_PORT:-8080}:8080"`
  is then correct as written (host side from the shell/.env, container side 8080).
- `docker-compose.yml` `healthcheck.test` — hit `:8080`, which is now always right.

Alternatively, make `ports:` and the healthcheck both use
`${TRDD_BE_HTTP_PORT}` on the container side too, matching the Dockerfile
healthcheck. Either is fine; today they contradict each other.
