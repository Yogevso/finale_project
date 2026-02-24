"""Topic normalization helpers shared across write and public-read paths."""

import re
from collections.abc import Iterable, Mapping
from typing import Optional


def slugify_topic(value: str) -> str:
    """Convert a topic-like label to a slug token."""
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def build_topic_lookup(topics: Iterable[object]) -> dict[str, str]:
    """Build alias->canonical-slug lookup from topic records."""
    lookup: dict[str, str] = {}
    for topic in topics:
        slug = str(getattr(topic, "slug", "") or "").strip()
        if not slug:
            continue

        canonical = slug
        lookup[slug.lower()] = canonical

        name = str(getattr(topic, "name", "") or "").strip()
        if name:
            lookup[name.lower()] = canonical
            name_slug = slugify_topic(name)
            if name_slug:
                lookup[name_slug] = canonical

    return lookup


def normalize_topic_to_slug(
    raw_topic: Optional[str], topic_lookup: Optional[Mapping[str, str]] = None
) -> Optional[str]:
    """Normalize incoming topic value into canonical slug form."""
    if raw_topic is None:
        return None

    value = raw_topic.strip()
    if not value:
        return None

    lowered = value.lower()
    if topic_lookup and lowered in topic_lookup:
        return topic_lookup[lowered]

    slugified = slugify_topic(value)
    if not slugified:
        return None

    if topic_lookup and slugified in topic_lookup:
        return topic_lookup[slugified]

    return slugified
