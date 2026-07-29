"""
Database connection setup.
Using SQLite for now (a single file 'fmms_simple.db' will be created automatically).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./fmms_simple.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Used in every route as a dependency.
    Opens a DB session, hands it to the route, closes it automatically when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
