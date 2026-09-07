# 008 — compose built a separate image per service, so rebuilds left services on stale code

- **Severity:** medium
- **Status:** done (fixed 2026-09-07 — commit `e3a01f4`)
- **Detected:** 2026-09-07, while verifying the migration for `005`
- **Area:** `backend/docker-compose.yml`

## Symptom

After adding migration `0008` and running `docker compose build backend`,
`docker compose run --rm seeder` failed:

```
alembic.util.exc.CommandError: Can't locate revision identified by
'0008_dedup_market_snapshots'
```

The `backend` container was already migrated to `0008`; the `seeder` running
against the same database could not find the `0008` script because its image
predated the migration.

## Root cause

`backend` and `seeder` both used the `x-backend` anchor's `build:` block but
had no explicit `image:` name, so compose built **two** images —
`tarakdingdung-backend` and `tarakdingdung-seeder` — from an identical build
config. `docker compose build backend` (and even a bare `docker compose build`
in this case) rebuilt only `tarakdingdung-backend`; `tarakdingdung-seeder`
stayed on whatever it was last built with. The result is exactly the
app/seeder code-and-schema skew the compose comment claims is impossible
("Shares the backend image, so it cannot seed with different code than the app
is running").

## Resolution

The `x-backend` anchor now pins `image: tarakdingdung-backend:latest`. With
one image name shared by every service, `docker compose build` builds it once
and `backend` + `seeder` (+ any future one-shot) always run identical code.

**Verified:** `docker rmi tarakdingdung-seeder:latest; docker compose build`
→ a single `tarakdingdung-backend:latest` image; `docker compose run --rm
seeder` migrates to `0008` and seeds; `docker compose up -d backend` → healthy.
