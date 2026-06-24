"""
Database connection setup.

We are using SQLite for now (temporary, for development/testing).
Later, switching to PostgreSQL only requires changing DATABASE_URL below
-- no other code changes needed, because SQLAlchemy handles both the same way.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ---- SQLite connection string ----
# This creates a file named "fmms.db" in the project root folder.
DATABASE_URL = "sqlite:///./fmms.db"

# connect_args is ONLY needed for SQLite (allows multiple threads to use the same connection)
# Remove connect_args when you switch to PostgreSQL later.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency function used in FastAPI routes.
    Opens a database session, gives it to the route, then closes it
    automatically once the request is done (even if there was an error).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
