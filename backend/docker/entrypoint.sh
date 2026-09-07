#!/bin/sh
# Container entrypoint.
#
# Migrations run before the app rather than from inside it: a process that
# migrates on startup races every other replica for the same schema lock, and a
# failed migration should stop the deploy rather than leave a server answering
# requests against a half-applied schema.
set -eu

migrate() {
    echo "running migrations..."
    python -c 'from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head
upgrade_to_head(Settings().postgres_dsn)'
}

case "${1:-serve}" in
    serve)
        migrate
        exec uvicorn tarakdingdung.main:app \
            --host "${TRDD_BE_HTTP_HOST:-0.0.0.0}" \
            --port "${TRDD_BE_HTTP_PORT:-8080}" \
            --no-server-header
        ;;
    migrate)
        migrate
        ;;
    seed)
        # Migrations first: seeding an unmigrated database fails on missing
        # tables, and the seeder is idempotent so a repeat run is harmless.
        migrate
        echo "seeding..."
        exec tarakdingdung-seed
        ;;
    *)
        # Anything else is run verbatim, so `docker compose run backend pytest`
        # and a debugging shell both work without a second image.
        exec "$@"
        ;;
esac
