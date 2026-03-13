"""Helpers for building stored reader artifacts from structured extraction results."""

from __future__ import annotations

from typing import Any

from app.conversion.ir import IRNode, count_ir_elements


def build_reader_artifact_from_extraction_result(result: Any) -> dict[str, Any]:
    """Normalize DOCX/PPTX extraction results into reader-artifact payloads."""
    toc_items = _build_toc_items(getattr(result, "headings", []))
    payload: dict[str, Any] = {
        "status": getattr(result, "status", "failed"),
        "title": getattr(result, "title", None),
        "metadata": dict(getattr(result, "metadata", {}) or {}),
        "headings": [_serialize_heading_item(item) for item in getattr(result, "headings", [])],
        "warnings": [_serialize_warning(item) for item in getattr(result, "warnings", [])],
        "confidence": float(getattr(result, "confidence", 0.0) or 0.0),
        "element_counts": count_ir_elements(getattr(result, "ir", None)),
        "toc_items": toc_items,
        "ir": _serialize_ir(getattr(result, "ir", None)),
    }

    slides = getattr(result, "slides", None)
    if slides is not None:
        payload["slides"] = [_serialize_slide_summary(item) for item in slides]

    extraction_error = getattr(result, "extraction_error", None)
    if extraction_error:
        payload["extraction_error"] = str(extraction_error)

    return {
        "status": payload["status"],
        "html_content": getattr(result, "html", "") or "",
        "toc_items": toc_items,
        "toc_source": "headings",
        "payload": payload,
        "error": extraction_error,
    }


def _build_toc_items(headings: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, heading in enumerate(headings):
        page_number = getattr(heading, "slide_number", None) or (index + 1)
        items.append(
            {
                "id": f"toc-{index}",
                "title": str(getattr(heading, "text", "") or "").strip(),
                "level": max(1, int(getattr(heading, "level", 1) or 1)),
                "page": page_number,
                "page_start": page_number,
                "page_end": None,
                "anchor_id": str(getattr(heading, "id", "") or "").strip(),
            }
        )
    return [item for item in items if item["title"]]


def _serialize_heading_item(item: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(item, "id", "") or ""),
        "level": int(getattr(item, "level", 1) or 1),
        "text": str(getattr(item, "text", "") or ""),
        "slide_number": getattr(item, "slide_number", None),
    }


def _serialize_warning(item: Any) -> dict[str, Any]:
    return {
        "code": str(getattr(item, "code", "") or ""),
        "message": str(getattr(item, "message", "") or ""),
        "count": getattr(item, "count", None),
    }


def _serialize_slide_summary(item: Any) -> dict[str, Any]:
    return {
        "number": int(getattr(item, "number", 0) or 0),
        "archive_path": str(getattr(item, "archive_path", "") or ""),
        "title": getattr(item, "title", None),
        "has_notes": bool(getattr(item, "has_notes", False)),
        "has_images": bool(getattr(item, "has_images", False)),
    }


def _serialize_ir(node: IRNode | None) -> dict[str, Any] | None:
    return node.to_dict() if node is not None else None
