"""Workflow DTO builders used by process-manager and handler tests."""

from __future__ import annotations

from app.schemas import DocumentCreate


def build_document_create(**overrides) -> DocumentCreate:
    payload = {
        "title": "Workflow Document",
        "description": "workflow",
        "status": "draft",
        "visibility": "internal",
        "category": "Uploaded",
        "tags": "",
        "parent_id": None,
    }
    payload.update(overrides)
    return DocumentCreate(**payload)
