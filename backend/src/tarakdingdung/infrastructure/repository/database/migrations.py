from pathlib import Path

import alembic.command
import alembic.config


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "alembic.ini").exists():
            return parent
    raise RuntimeError("alembic.ini not found above the package")


def upgrade_to_head(dsn: str) -> None:
    root = _project_root()
    config = alembic.config.Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database" / "migrations"))
    config.set_main_option("sqlalchemy.url", dsn)
    alembic.command.upgrade(config, "head")
