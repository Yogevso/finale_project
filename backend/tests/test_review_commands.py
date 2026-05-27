"""Regression tests for review command handlers."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.commands.review_commands import (
    ApproveReviewCommand,
    ApproveReviewCommandHandler,
)
from app.application.pipeline import CommandContext
from app.db import Base
from app.db.bases import AnalyticsBase, ChatBase
from app.errors import ConflictError
from app.models import DocumentStatus, ReviewRequest, ReviewStatus, User, UserRole
from tests.factories import create_document, create_tenant, create_user


def test_approve_review_blocks_stale_concurrent_overwrite(tmp_path):
    sqlite_path = tmp_path / "approve_review_race.db"
    engine = create_engine(
        f"sqlite:///{sqlite_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    AnalyticsBase.metadata.create_all(bind=engine)
    ChatBase.metadata.create_all(bind=engine)

    seed_session = SessionLocal()
    verifier_session = None
    reviewer_session_one = None
    reviewer_session_two = None
    try:
        tenant = create_tenant(
            seed_session,
            name="Review Race Tenant",
            slug=f"review-race-{uuid4().hex[:8]}",
        )
        submitter = create_user(
            seed_session,
            username=f"submitter-{uuid4().hex[:6]}",
            email=f"submitter-{uuid4().hex[:6]}@example.com",
            role=UserRole.EDITOR,
            tenant_id=tenant.id,
        )
        reviewer_one = create_user(
            seed_session,
            username=f"reviewer-one-{uuid4().hex[:6]}",
            email=f"reviewer-one-{uuid4().hex[:6]}@example.com",
            role=UserRole.MANAGER,
            tenant_id=tenant.id,
            full_name="Reviewer One",
        )
        reviewer_two = create_user(
            seed_session,
            username=f"reviewer-two-{uuid4().hex[:6]}",
            email=f"reviewer-two-{uuid4().hex[:6]}@example.com",
            role=UserRole.ADMIN,
            tenant_id=tenant.id,
            full_name="Reviewer Two",
        )
        document = create_document(
            seed_session,
            title="Race Review Document",
            document_number=f"DOC-RACE-{uuid4().hex[:8].upper()}",
            status=DocumentStatus.PENDING_REVIEW,
            created_by=submitter.id,
            tenant_id=tenant.id,
        )
        review = ReviewRequest(
            document_id=document.id,
            submitted_by=submitter.id,
            status=ReviewStatus.PENDING,
            message="Please approve",
        )
        seed_session.add(review)
        seed_session.commit()
        seed_session.refresh(review)
        review_id = review.id
        document_id = document.id
        reviewer_one_id = reviewer_one.id
        reviewer_two_id = reviewer_two.id
    finally:
        seed_session.close()

    reviewer_session_one = SessionLocal()
    reviewer_session_two = SessionLocal()
    verifier_session = SessionLocal()
    try:
        reviewer_one = reviewer_session_one.get(User, reviewer_one_id)
        reviewer_two = reviewer_session_two.get(User, reviewer_two_id)
        assert reviewer_one is not None
        assert reviewer_two is not None

        handler_one = ApproveReviewCommandHandler(reviewer_session_one)
        handler_two = ApproveReviewCommandHandler(reviewer_session_two)

        context_one = CommandContext(
            command=ApproveReviewCommand(
                review_id=review_id,
                comments="First approval wins",
                review_feedback=None,
                current_user=reviewer_one,
            )
        )
        context_two = CommandContext(
            command=ApproveReviewCommand(
                review_id=review_id,
                comments="Second approval must lose",
                review_feedback=None,
                current_user=reviewer_two,
            )
        )

        handler_one._validate(context_one)
        handler_one._authorize(context_one)
        handler_two._validate(context_two)
        handler_two._authorize(context_two)

        approved_review = handler_one._execute_command(context_one)
        assert approved_review.status == ReviewStatus.APPROVED
        assert approved_review.reviewed_by == reviewer_one.id
        assert approved_review.review_comments == "First approval wins"

        with pytest.raises(
            ConflictError,
            match="already been processed by another reviewer",
        ):
            handler_two._execute_command(context_two)

        stored_review = (
            verifier_session.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        )
        assert stored_review is not None
        assert stored_review.status == ReviewStatus.APPROVED
        assert stored_review.reviewed_by == reviewer_one.id
        assert stored_review.review_comments == "First approval wins"

        stored_document = verifier_session.get(type(document), document_id)
        assert stored_document is not None
        assert stored_document.status == DocumentStatus.APPROVED
    finally:
        if verifier_session is not None:
            verifier_session.close()
        if reviewer_session_two is not None:
            reviewer_session_two.close()
        if reviewer_session_one is not None:
            reviewer_session_one.close()
        engine.dispose()
