"""FastAPI dependency functions for database sessions."""

from app.db.sessions import AnalyticsSessionLocal, ChatSessionLocal, CoreSessionLocal


def get_core_db():
    """Dependency to get a Core database session."""
    db = CoreSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_analytics_db():
    """Dependency to get an Analytics database session."""
    db = AnalyticsSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chat_db():
    """Dependency to get a Chat database session."""
    db = ChatSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Backward compatibility — use get_core_db() for new code
get_db = get_core_db
