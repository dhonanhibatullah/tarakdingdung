from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[5]


def alembic_config(dsn: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "database" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", dsn)
    return cfg


def upgrade_to_head(dsn: str) -> None:
    command.upgrade(alembic_config(dsn), "head")


def downgrade_to_base(dsn: str) -> None:
    command.downgrade(alembic_config(dsn), "base")
