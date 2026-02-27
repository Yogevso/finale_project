"""Topic normalization helpers shared across write and public-read paths."""

from collections.abc import Iterable, Mapping
from typing import Optional

from app.domain.value_objects import TopicSlug


def slugify_topic(value: str) -> str:
    """Convert a topic-like label to a slug token."""
    return TopicSlug.slugify(value)


def build_topic_lookup(topics: Iterable[object]) -> dict[str, str]:
    """Build alias->canonical-slug lookup from topic records."""
    lookup: dict[str, str] = {}
    for topic in topics:
        slug = str(getattr(topic, "slug", "") or "").strip()
        canonical_slug = TopicSlug.from_raw(slug)
        if canonical_slug is None:
            continue

        canonical = canonical_slug.value
        lookup[canonical] = canonical
        lookup[slug.lower()] = canonical

        name = str(getattr(topic, "name", "") or "").strip()
        if name:
            lookup[name.lower()] = canonical
            name_slug = TopicSlug.slugify(name)
            if name_slug:
                lookup[name_slug] = canonical

    return lookup


def normalize_topic_to_slug(
    raw_topic: Optional[str], topic_lookup: Optional[Mapping[str, str]] = None
) -> Optional[str]:
    """Normalize incoming topic value into canonical slug form."""
    normalized = TopicSlug.normalize(raw_topic, topic_lookup)
    return normalized.value if normalized else None
