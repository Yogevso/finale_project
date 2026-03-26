"""In-process domain event dispatcher."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, TypeVar

from app.domain.events.events import DomainEvent

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT", bound=DomainEvent)


class InProcessDomainEventDispatcher:
    """Simple synchronous dispatcher designed for outbox evolution later."""

    def __init__(self, *, suppress_handler_exceptions: bool = True) -> None:
        self._handlers: dict[type[DomainEvent], list[Callable[[DomainEvent], None]]] = defaultdict(
            list
        )
        self._suppress_handler_exceptions = suppress_handler_exceptions

    def register(self, event_type: type[EventT], handler: Callable[[EventT], None]) -> None:
        self._handlers[event_type].append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # policy: LOSSY — one failing subscriber must not block the event fan-out
                logger.exception(
                    "Domain event handler failed for %s",
                    type(event).__name__,
                )
                if not self._suppress_handler_exceptions:
                    raise
