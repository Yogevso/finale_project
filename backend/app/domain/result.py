"""Typed Result algebra for expected domain/application outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, cast

T = TypeVar("T")
E = TypeVar("E")

_MISSING = object()


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """A typed success/error container for expected failures."""

    _value: T | object = _MISSING
    _error: E | object = _MISSING

    def __post_init__(self) -> None:
        has_value = self._value is not _MISSING
        has_error = self._error is not _MISSING
        if has_value == has_error:
            raise ValueError("Result must contain exactly one of value or error")

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        return cls(_value=value)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
        return cls(_error=error)

    @property
    def is_ok(self) -> bool:
        return self._error is _MISSING

    @property
    def is_err(self) -> bool:
        return self._error is not _MISSING

    @property
    def value(self) -> T:
        if self.is_err:
            raise RuntimeError("Cannot access value of an error result")
        return cast(T, self._value)

    @property
    def error(self) -> E:
        if self.is_ok:
            raise RuntimeError("Cannot access error of a successful result")
        return cast(E, self._error)
