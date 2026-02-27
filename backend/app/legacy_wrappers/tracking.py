"""Usage and migration tracking for legacy strangler wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class LegacyWrapperStatus:
    """Snapshot status for one legacy wrapper boundary."""

    wrapper_name: str
    legacy_module: str
    migration_completion_percent: int
    call_volume: int


class LegacyWrapperTracker:
    """Thread-safe in-memory tracker for wrapper usage and migration progress."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._metadata: dict[str, tuple[str, int]] = {}
        self._call_volume: dict[str, int] = {}

    def register_wrapper(
        self,
        *,
        wrapper_name: str,
        legacy_module: str,
        migration_completion_percent: int = 0,
    ) -> None:
        completion = min(100, max(0, int(migration_completion_percent)))
        with self._lock:
            self._metadata[wrapper_name] = (legacy_module, completion)
            self._call_volume.setdefault(wrapper_name, 0)

    def increment_call(self, wrapper_name: str) -> None:
        with self._lock:
            self._call_volume[wrapper_name] = self._call_volume.get(wrapper_name, 0) + 1

    def statuses(self) -> list[LegacyWrapperStatus]:
        with self._lock:
            statuses: list[LegacyWrapperStatus] = []
            for wrapper_name, (legacy_module, completion) in sorted(self._metadata.items()):
                statuses.append(
                    LegacyWrapperStatus(
                        wrapper_name=wrapper_name,
                        legacy_module=legacy_module,
                        migration_completion_percent=completion,
                        call_volume=self._call_volume.get(wrapper_name, 0),
                    )
                )
            return statuses

    def reset(self) -> None:
        with self._lock:
            for wrapper_name in list(self._call_volume.keys()):
                self._call_volume[wrapper_name] = 0


_tracker = LegacyWrapperTracker()


def get_legacy_wrapper_tracker() -> LegacyWrapperTracker:
    """Get singleton tracker for wrapper boundaries."""
    return _tracker
