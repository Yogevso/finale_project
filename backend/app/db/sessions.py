"""Session factories for Core, Analytics, and Chat databases."""

from sqlalchemy.orm import sessionmaker

from app.db.engines import analytics_engine, chat_engine, core_engine

CoreSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=core_engine)
AnalyticsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=analytics_engine)
ChatSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=chat_engine)

# Backward compatibility
SessionLocal = CoreSessionLocal
