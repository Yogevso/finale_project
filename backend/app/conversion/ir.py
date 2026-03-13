"""Shared intermediate representation for extracted DOCX/PPTX content."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IRNode:
    """Serializable intermediate representation node used before HTML rendering."""

    type: str
    content: str = ""
    styles: dict[str, Any] = field(default_factory=dict)
    children: list["IRNode"] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the node tree."""
        payload: dict[str, Any] = {
            "type": self.type,
            "content": self.content,
            "styles": _serialize_value(self.styles),
            "children": [child.to_dict() for child in self.children],
        }
        if self.attributes:
            payload["attributes"] = _serialize_value(self.attributes)
        return payload


def count_ir_elements(node: IRNode | None) -> dict[str, int]:
    """Count node types across an IR tree for artifact metadata."""
    if node is None:
        return {}

    counter: Counter[str] = Counter()
    _count_node_types(node, counter)
    return dict(sorted(counter.items()))


def _count_node_types(node: IRNode, counter: Counter[str]) -> None:
    counter[node.type] += 1
    for child in node.children:
        _count_node_types(child, counter)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, IRNode):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    return value
