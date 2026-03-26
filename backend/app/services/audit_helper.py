"""Audit log and security event write helpers for multi-DB architecture.

These helpers write to the analytics database independently of the core
transaction, using a standalone session from AnalyticsSessionLocal.
"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Overridable session factory for testing.
_session_factory_override: Callable | None = None


def set_session_factory(factory: Callable | None) -> None:
    """Override the session factory (for tests). Pass None to reset."""
    global _session_factory_override
    _session_factory_override = factory


def _get_session():
    if _session_factory_override is not None:
        return _session_factory_override()
    from app.db import AnalyticsSessionLocal
    return AnalyticsSessionLocal()


def write_audit_log(**kwargs) -> None:
    """Write an AuditLog entry to the analytics database.

    Accepts the same keyword arguments as the AuditLog constructor
    (user_id, action, details, document_id, etc.).
    """
    from app.models import AuditLog

    session = _get_session()
    try:
        session.add(AuditLog(**kwargs))
        session.commit()
    except Exception:  # policy: LOSSY — analytics-side audit writes must not block the primary transaction
        session.rollback()
        logger.warning("Failed to write audit log entry", exc_info=True)
    finally:
        session.close()


def write_security_event(**kwargs) -> None:
    """Write a SecurityEvent entry to the analytics database.

    Accepts the same keyword arguments as the SecurityEvent constructor
    (user_id, event_type, ip_address, user_agent).
    """
    from app.models import SecurityEvent

    session = _get_session()
    try:
        session.add(SecurityEvent(**kwargs))
        session.commit()
    except Exception:  # policy: LOSSY — analytics-side security writes must not block the primary transaction
        session.rollback()
        logger.warning("Failed to write security event", exc_info=True)
    finally:
        session.close()
