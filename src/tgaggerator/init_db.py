from tgaggerator.db import engine
from tgaggerator.migrations import upgrade_head
from tgaggerator.models import Base


def init_db() -> None:
    """Primary schema init path via Alembic migrations."""
    upgrade_head()


def init_db_for_tests() -> None:
    """Lightweight schema init for unit tests."""
    Base.metadata.create_all(bind=engine)
