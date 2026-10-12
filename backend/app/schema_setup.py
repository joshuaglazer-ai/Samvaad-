"""Bring the database schema up to date via Alembic (so seed scripts and the app agree)."""
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def upgrade_to_head() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")
