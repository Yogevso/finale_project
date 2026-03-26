"""Tests for assistant-visible document version selection."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.assistant.rag.indexer import DocumentIndexer
from app.assistant.tools.document_tools import GetDocumentTool
from app.assistant.tools.info_tools import GetDocumentContentTool
from app.assistant.tools.rag_tools import AskAboutDocumentTool, SummarizeDocumentTool
from app.models import DocumentStatus, DocumentVisibility, UserRole, Version
from tests.factories import create_document, create_tenant, create_user


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _create_versioned_document(db, *, owner, tenant_id: int):
    document = create_document(
        db,
        title="Assistant Visible Version Doc",
        created_by=owner.id,
        tenant_id=tenant_id,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
    )
    published_version = Version(
        document_id=document.id,
        version_number=1,
        content="<p>PUBLISHED_VISIBLE_CONTENT</p>",
        created_by=owner.id,
        is_published=True,
        published_at=datetime.utcnow() - timedelta(days=1),
        published_by=owner.id,
    )
    draft_version = Version(
        document_id=document.id,
        version_number=2,
        content="<p>DRAFT_INTERNAL_CONTENT</p>",
        created_by=owner.id,
        is_published=False,
    )
    db.add_all([published_version, draft_version])
    db.commit()
    db.refresh(document)
    return document


def test_summarize_document_customer_uses_latest_published_version(db):
    tenant = create_tenant(db, name="Assistant Published Tenant")
    owner = create_user(
        db,
        email="assistant-published-owner@example.com",
        username="assistant_published_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    customer = create_user(
        db,
        email="assistant-published-customer@example.com",
        username="assistant_published_customer",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)

    with patch(
        "app.assistant.ollama_client.OllamaClient.chat",
        new=AsyncMock(return_value={"message": {"content": "summary"}}),
    ) as mock_chat:
        result = _run(
            SummarizeDocumentTool().execute(
                customer,
                tenant.id,
                {"document_id": document.id},
                db,
            )
        )

    assert result["success"] is True
    prompt = mock_chat.await_args.kwargs["messages"][1]["content"]
    assert "PUBLISHED_VISIBLE_CONTENT" in prompt
    assert "DRAFT_INTERNAL_CONTENT" not in prompt


def test_summarize_document_internal_user_uses_latest_draft_version(db):
    tenant = create_tenant(db, name="Assistant Draft Tenant")
    owner = create_user(
        db,
        email="assistant-draft-owner@example.com",
        username="assistant_draft_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    editor = create_user(
        db,
        email="assistant-draft-editor@example.com",
        username="assistant_draft_editor",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)

    with patch(
        "app.assistant.ollama_client.OllamaClient.chat",
        new=AsyncMock(return_value={"message": {"content": "summary"}}),
    ) as mock_chat:
        result = _run(
            SummarizeDocumentTool().execute(
                editor,
                tenant.id,
                {"document_id": document.id},
                db,
            )
        )

    assert result["success"] is True
    prompt = mock_chat.await_args.kwargs["messages"][1]["content"]
    assert "DRAFT_INTERNAL_CONTENT" in prompt
    assert "PUBLISHED_VISIBLE_CONTENT" not in prompt


def test_ask_about_document_customer_uses_latest_published_version(db):
    tenant = create_tenant(db, name="Assistant Ask Tenant")
    owner = create_user(
        db,
        email="assistant-ask-owner@example.com",
        username="assistant_ask_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    customer = create_user(
        db,
        email="assistant-ask-customer@example.com",
        username="assistant_ask_customer",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)

    with patch(
        "app.assistant.ollama_client.OllamaClient.chat",
        new=AsyncMock(return_value={"message": {"content": "answer"}}),
    ) as mock_chat:
        result = _run(
            AskAboutDocumentTool().execute(
                customer,
                tenant.id,
                {"document_id": document.id, "question": "What does it say?"},
                db,
            )
        )

    assert result["success"] is True
    prompt = mock_chat.await_args.kwargs["messages"][1]["content"]
    assert "PUBLISHED_VISIBLE_CONTENT" in prompt
    assert "DRAFT_INTERNAL_CONTENT" not in prompt


def test_get_document_content_customer_returns_latest_published_version(db):
    tenant = create_tenant(db, name="Assistant Content Tenant")
    owner = create_user(
        db,
        email="assistant-content-owner@example.com",
        username="assistant_content_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    customer = create_user(
        db,
        email="assistant-content-customer@example.com",
        username="assistant_content_customer",
        role=UserRole.CUSTOMER,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)

    result = _run(
        GetDocumentContentTool().execute(
            customer,
            tenant.id,
            {"document_id": document.id},
            db,
        )
    )

    assert result["success"] is True
    assert "PUBLISHED_VISIBLE_CONTENT" in result["result"]
    assert "DRAFT_INTERNAL_CONTENT" not in result["result"]


def test_get_document_content_internal_user_denied_cross_tenant_internal_document(db):
    tenant_a = create_tenant(db, name="Assistant Content Tenant A")
    tenant_b = create_tenant(db, name="Assistant Content Tenant B")
    requester = create_user(
        db,
        email="assistant-cross-tenant-requester@example.com",
        username="assistant_cross_tenant_requester",
        role=UserRole.EDITOR,
        tenant_id=tenant_a.id,
    )
    owner = create_user(
        db,
        email="assistant-cross-tenant-owner@example.com",
        username="assistant_cross_tenant_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant_b.id,
    )
    document = create_document(
        db,
        title="Cross Tenant Internal Doc",
        created_by=owner.id,
        tenant_id=tenant_b.id,
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
    )
    db.add(
        Version(
            document_id=document.id,
            version_number=1,
            content="<p>CROSS_TENANT_INTERNAL_CONTENT</p>",
            created_by=owner.id,
        )
    )
    db.commit()

    result = _run(
        GetDocumentContentTool().execute(
            requester,
            tenant_a.id,
            {"document_id": document.id},
            db,
        )
    )

    assert result["success"] is False
    assert result["error"] == "You do not have access to this document."


def test_get_document_internal_user_uses_latest_draft_preview(db):
    tenant = create_tenant(db, name="Assistant Metadata Tenant")
    owner = create_user(
        db,
        email="assistant-metadata-owner@example.com",
        username="assistant_metadata_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    editor = create_user(
        db,
        email="assistant-metadata-editor@example.com",
        username="assistant_metadata_editor",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)

    result = _run(
        GetDocumentTool().execute(
            editor,
            tenant.id,
            {"document_id": document.id},
            db,
        )
    )

    assert result["success"] is True
    assert "DRAFT_INTERNAL_CONTENT" in result["result"]
    assert "PUBLISHED_VISIBLE_CONTENT" not in result["result"]


def test_reindex_all_indexes_latest_version_for_internal_semantic_search(db):
    tenant = create_tenant(db, name="Assistant Index Tenant")
    owner = create_user(
        db,
        email="assistant-index-owner@example.com",
        username="assistant_index_owner",
        role=UserRole.EDITOR,
        tenant_id=tenant.id,
    )
    document = _create_versioned_document(db, owner=owner, tenant_id=tenant.id)
    indexer = DocumentIndexer(
        embeddings=MagicMock(),
        vector_store=MagicMock(),
        chunker=MagicMock(),
    )

    with patch.object(indexer, "index_document", new=AsyncMock(return_value=2)) as mock_index_document:
        stats = _run(indexer.reindex_all(db))

    assert stats["documents_indexed"] == 1
    assert stats["total_chunks"] == 2
    assert mock_index_document.await_count == 1
    assert mock_index_document.await_args.args[0] == document.id
    assert "DRAFT_INTERNAL_CONTENT" in mock_index_document.await_args.args[2]
    assert "PUBLISHED_VISIBLE_CONTENT" not in mock_index_document.await_args.args[2]
