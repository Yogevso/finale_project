"""Semantic version value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SemanticVersion:
    """Immutable semantic version with domain bump operations."""

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("semantic version components must be non-negative")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def initial(cls) -> SemanticVersion:
        return cls(1, 0, 0)

    @classmethod
    def try_parse(cls, raw_value: Optional[str]) -> Optional[SemanticVersion]:
        if raw_value:
            parts = raw_value.strip().split(".")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        return None

    @classmethod
    def from_raw(cls, raw_value: Optional[str], fallback_major: int = 1) -> SemanticVersion:
        parsed = cls.try_parse(raw_value)
        if parsed is not None:
            return parsed
        base = fallback_major if fallback_major > 0 else 1
        return cls(base, 0, 0)

    def bump_major(self) -> SemanticVersion:
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> SemanticVersion:
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> SemanticVersion:
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def bumped(self, bump_type: object) -> SemanticVersion:
        value = str(getattr(bump_type, "value", bump_type or "")).strip().lower()
        if value == "major":
            return self.bump_major()
        if value == "minor":
            return self.bump_minor()
        return self.bump_patch()

