"""Legacy strangler wrappers public API.

AF-013: These wrappers are *active* migration boundaries. They track
usage of legacy utility modules while new implementations are built
inside ``app.conversion`` / ``app.services``. Each wrapper records
call counts so we know when usage reaches zero and the legacy module
can be deleted.

Current migration status:
  - document_converter: 0% (target: app.conversion pipeline)
  - analytics: tracked via wrapper
"""

from app.legacy_wrappers.analytics import AnalyticsServiceStranglerWrapper
from app.legacy_wrappers.document_converter import (
    DocumentConverterStranglerWrapper,
    get_document_converter_wrapper,
)
from app.legacy_wrappers.tracking import (
    LegacyWrapperStatus,
    LegacyWrapperTracker,
    get_legacy_wrapper_tracker,
)

__all__ = [
    "AnalyticsServiceStranglerWrapper",
    "DocumentConverterStranglerWrapper",
    "LegacyWrapperStatus",
    "LegacyWrapperTracker",
    "get_document_converter_wrapper",
    "get_legacy_wrapper_tracker",
]
