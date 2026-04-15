"""Document number value object."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

_DATE_KEY_PATTERN = re.compile(r"^\d{8}$")
_DOCUMENT_NUMBER_PATTERN = re.compile(r"^DOC-(\d{8})-(\d+)$")


@dataclass(frozen=True)
class DocumentNumber:
    """Canonical document number in DOC-YYYYMMDD-XXXX form."""

    date_key: str
    sequence: int

    def __post_init__(self) -> None:
        if not _DATE_KEY_PATTERN.match(self.date_key):
            raise ValueError("date_key must be an 8-digit YYYYMMDD string")
        if self.sequence <= 0:
            raise ValueError("sequence must be a positive integer")

    @property
    def prefix(self) -> str:
        return f"DOC-{self.date_key}"

    def __str__(self) -> str:
        return f"{self.prefix}-{self.sequence:04d}"

    @classmethod
    def from_date_key(cls, date_key: str, sequence: int) -> DocumentNumber:
        return cls(date_key=date_key, sequence=sequence)

    @classmethod
    def for_utc_now(cls, sequence: int, *, now: Optional[datetime] = None) -> DocumentNumber:
        current = now or datetime.utcnow()
        return cls(date_key=current.strftime("%Y%m%d"), sequence=sequence)

    @classmethod
    def parse(cls, value: str) -> DocumentNumber:
        match = _DOCUMENT_NUMBER_PATTERN.match((value or "").strip())
        if not match:
            raise ValueError("Invalid document number format")
        date_key, suffix = match.group(1), match.group(2)
        return cls(date_key=date_key, sequence=int(suffix))

    @staticmethod
    def prefix_for_date_key(date_key: str) -> str:
        if not _DATE_KEY_PATTERN.match(date_key):
            raise ValueError("date_key must be an 8-digit YYYYMMDD string")
        return f"DOC-{date_key}"

    @staticmethod
    def extract_sequence_suffix(document_number: str, prefix: str) -> Optional[int]:
        expected_prefix = f"{prefix}-"
        if not document_number or not document_number.startswith(expected_prefix):
            return None

        suffix = document_number[len(expected_prefix) :]
        if not suffix.isdigit():
            return None
        return int(suffix)
