"""Engagement tools — bookmarks, watchers, reading progress."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import (
    Bookmark,
    Document,
    DocumentWatcher,
    ReadingProgress,
    User,
)
from app.services.permissions import Permission


class BookmarkDocumentTool(BaseTool):
    name = "bookmark_document"
    description = "Add a document to your bookmarks for quick access later."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to bookmark"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        existing = (
            db.query(Bookmark)
            .filter(Bookmark.user_id == user.id, Bookmark.document_id == doc_id)
            .first()
        )
        if existing:
            return {"success": True, "result": "Document is already bookmarked."}
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "result": f"Document {doc_id} not found."}
        # AE-009: Tenant isolation — prevent cross-tenant bookmarking
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": f"Document {doc_id} not found."}
        bm = Bookmark(user_id=user.id, document_id=doc_id)
        db.add(bm)
        db.commit()
        return {"success": True, "result": f"Bookmarked document '{doc.title}' (ID: {doc_id})."}


class RemoveBookmarkTool(BaseTool):
    name = "remove_bookmark"
    description = "Remove a document from your bookmarks."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to un-bookmark"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        bm = (
            db.query(Bookmark)
            .filter(Bookmark.user_id == user.id, Bookmark.document_id == params["document_id"])
            .first()
        )
        if not bm:
            return {"success": True, "result": "That document is not in your bookmarks."}
        db.delete(bm)
        db.commit()
        return {"success": True, "result": "Bookmark removed."}


class ListMyBookmarksTool(BaseTool):
    name = "list_my_bookmarks"
    description = "List all documents you have bookmarked."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        bookmarks = (
            db.query(Bookmark)
            .filter(Bookmark.user_id == user.id)
            .order_by(Bookmark.created_at.desc())
            .limit(limit)
            .all()
        )
        if not bookmarks:
            return {"success": True, "result": "You have no bookmarks yet."}
        lines = [f"{len(bookmarks)} bookmark(s):"]
        for bm in bookmarks:
            doc = db.query(Document).filter(Document.id == bm.document_id).first()
            title = doc.title if doc else "(deleted)"
            lines.append(f"- [{bm.document_id}] {title} (bookmarked {bm.created_at:%Y-%m-%d})")
        return {"success": True, "result": "\n".join(lines)}


class WatchDocumentTool(BaseTool):
    name = "watch_document"
    description = "Start watching a document to get notifications about changes."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to watch"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        existing = (
            db.query(DocumentWatcher)
            .filter(DocumentWatcher.user_id == user.id, DocumentWatcher.document_id == doc_id)
            .first()
        )
        if existing:
            return {"success": True, "result": "You are already watching this document."}
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "result": f"Document {doc_id} not found."}
        # AE-009: Tenant isolation — prevent cross-tenant watching
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": f"Document {doc_id} not found."}
        watcher = DocumentWatcher(user_id=user.id, document_id=doc_id)
        db.add(watcher)
        db.commit()
        return {
            "success": True,
            "result": f"Now watching '{doc.title}' — you'll be notified of changes.",
        }


class UnwatchDocumentTool(BaseTool):
    name = "unwatch_document"
    description = "Stop watching a document."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to unwatch"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        w = (
            db.query(DocumentWatcher)
            .filter(
                DocumentWatcher.user_id == user.id,
                DocumentWatcher.document_id == params["document_id"],
            )
            .first()
        )
        if not w:
            return {"success": True, "result": "You are not watching that document."}
        db.delete(w)
        db.commit()
        return {"success": True, "result": "Stopped watching the document."}


class GetMyWatchedDocumentsTool(BaseTool):
    name = "get_my_watched_documents"
    description = "List all documents you are watching for updates."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        watchers = (
            db.query(DocumentWatcher)
            .filter(DocumentWatcher.user_id == user.id)
            .order_by(DocumentWatcher.created_at.desc())
            .limit(limit)
            .all()
        )
        if not watchers:
            return {"success": True, "result": "You are not watching any documents."}
        lines = [f"Watching {len(watchers)} document(s):"]
        for w in watchers:
            doc = db.query(Document).filter(Document.id == w.document_id).first()
            title = doc.title if doc else "(deleted)"
            lines.append(f"- [{w.document_id}] {title} (since {w.created_at:%Y-%m-%d})")
        return {"success": True, "result": "\n".join(lines)}


class GetReadingProgressTool(BaseTool):
    name = "get_reading_progress"
    description = "Check your reading progress on a specific document or all documents."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "Specific document ID (omit for all)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results when listing all (default 20)",
            },
        },
        "required": [],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        doc_id = params.get("document_id")
        if doc_id:
            rp = (
                db.query(ReadingProgress)
                .filter(ReadingProgress.user_id == user.id, ReadingProgress.document_id == doc_id)
                .first()
            )
            if not rp:
                return {
                    "success": True,
                    "result": f"No reading progress recorded for document {doc_id}.",
                }
            status = "completed" if rp.completed_at else f"{rp.progress_percent}%"
            return {
                "success": True,
                "result": f"Document {doc_id}: {status} (last read {rp.last_read_at:%Y-%m-%d %H:%M}).",
            }
        # All progress
        limit = min(params.get("limit", 20), 50)
        records = (
            db.query(ReadingProgress)
            .filter(ReadingProgress.user_id == user.id)
            .order_by(ReadingProgress.last_read_at.desc())
            .limit(limit)
            .all()
        )
        if not records:
            return {"success": True, "result": "No reading progress recorded yet."}
        lines = [f"{len(records)} document(s) with progress:"]
        for rp in records:
            doc = db.query(Document).filter(Document.id == rp.document_id).first()
            title = doc.title if doc else "(deleted)"
            status = "done" if rp.completed_at else f"{rp.progress_percent}%"
            lines.append(f"- [{rp.document_id}] {title}: {status}")
        return {"success": True, "result": "\n".join(lines)}


class UpdateReadingProgressTool(BaseTool):
    name = "update_reading_progress"
    description = "Update your reading progress on a document (0-100%)."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "progress_percent": {"type": "integer", "description": "Progress from 0 to 100"},
        },
        "required": ["document_id", "progress_percent"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        pct = max(0, min(100, params["progress_percent"]))
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "result": f"Document {doc_id} not found."}
        # AE-009: Tenant isolation — prevent cross-tenant reading progress updates
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": f"Document {doc_id} not found."}
        rp = (
            db.query(ReadingProgress)
            .filter(ReadingProgress.user_id == user.id, ReadingProgress.document_id == doc_id)
            .first()
        )
        now = datetime.utcnow()
        if rp:
            rp.progress_percent = pct
            rp.last_read_at = now
            if pct >= 100 and not rp.completed_at:
                rp.completed_at = now
        else:
            rp = ReadingProgress(
                user_id=user.id,
                document_id=doc_id,
                progress_percent=pct,
                last_read_at=now,
                completed_at=now if pct >= 100 else None,
            )
            db.add(rp)
        db.commit()
        status = "Complete!" if pct >= 100 else f"{pct}%"
        return {
            "success": True,
            "result": f"Reading progress for '{doc.title}' updated to {status}.",
        }
