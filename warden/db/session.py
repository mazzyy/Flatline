"""Engine and session factory.

Tests and `make demo-test` use SQLite. Docker / Render use Postgres.
Sync SQLAlchemy is the simpler option and is what every request path uses
(D-005).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warden.config import settings
from warden.db.base import Base
from warden.db.models import DEFAULT_SHOP_CONFIG, ShopConfigVersion

_ENGINE: Engine | None = None
_SESSION: sessionmaker[Session] | None = None


def _sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def make_engine(url: str | None = None) -> Engine:
    url = url or settings().database_url
    # Tests pass sqlite+aiosqlite; we only speak the sync driver.
    url = url.replace("sqlite+aiosqlite", "sqlite")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if _sqlite_url(url):
        kwargs.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, **kwargs)


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = make_engine()
        if _sqlite_url(str(_ENGINE.url)):

            @event.listens_for(_ENGINE, "connect")
            def _fk(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _ENGINE


def get_sessionmaker() -> sessionmaker[Session]:
    global _SESSION
    if _SESSION is None:
        _SESSION = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SESSION


def reset_engine() -> None:
    global _ENGINE, _SESSION
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION = None


def create_schema(engine: Engine | None = None) -> None:
    create_engine_ = engine or get_engine()
    Base.metadata.create_all(create_engine_)


def ensure_default_config(session: Session) -> ShopConfigVersion:
    existing = session.scalar(select(ShopConfigVersion).where(ShopConfigVersion.active.is_(True)))
    if existing:
        return existing
    row = ShopConfigVersion(
        version=1, config=dict(DEFAULT_SHOP_CONFIG), author="human", active=True, note="initial"
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def session_dep() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
