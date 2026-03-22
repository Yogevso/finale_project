"""Declarative Base classes for the multi-database architecture.

Three separate Base classes allow SQLAlchemy to track which models
belong to which database, enabling independent metadata.create_all()
and Alembic migration targets.
"""

from sqlalchemy.orm import declarative_base

CoreBase = declarative_base()
AnalyticsBase = declarative_base()
ChatBase = declarative_base()

# Backward compatibility — existing code imports `Base` from `app.db`
Base = CoreBase
