"""Topic slug value object."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class TopicSlug:
    """Canonical topic slug value object."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not _SLUG_PATTERN.match(self.value):
            raise ValueError("topic slug must match [a-z0-9]+(-[a-z0-9]+)*")

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")

    @classmethod
    def from_raw(cls, raw_topic: Optional[str]) -> Optional[TopicSlug]:
        if raw_topic is None:
            return None
        slug = cls.slugify(raw_topic)
        if not slug:
            return None
        return cls(slug)

    @classmethod
    def normalize(
        cls,
        raw_topic: Optional[str],
        topic_lookup: Optional[Mapping[str, str]] = None,
    ) -> Optional[TopicSlug]:
        if raw_topic is None:
            return None

        value = raw_topic.strip()
        if not value:
            return None

        lowered = value.lower()
        if topic_lookup and lowered in topic_lookup:
            canonical = cls.slugify(str(topic_lookup[lowered]))
            if canonical:
                return cls(canonical)

        slugified = cls.slugify(value)
        if not slugified:
            return None

        if topic_lookup and slugified in topic_lookup:
            canonical = cls.slugify(str(topic_lookup[slugified]))
            if canonical:
                return cls(canonical)

        return cls(slugified)
