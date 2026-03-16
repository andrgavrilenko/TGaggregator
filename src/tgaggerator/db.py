from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tgaggerator.config import settings


engine = create_engine(
    settings.db_url,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.db_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=True, autocommit=False, class_=Session)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
