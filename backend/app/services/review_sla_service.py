"""Review workflow SLA processing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Document, NotificationType, ReviewRequest, ReviewStatus, User, UserRole
from app.schemas import ReviewSlaItem, ReviewSlaProcessResponse
from app.services.notification_service import NotificationService


@dataclass(slots=True)
class ReviewSlaThresholds:
    """Configurable SLA thresholds for pending reviews."""

    reminder_hours: int
    escalation_hours: int


class ReviewSlaService:
    """Scan pending reviews and emit reminder/escalation notifications."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def _pending_reviews(self, actor: User) -> list[ReviewRequest]:
        query = (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.document),
                joinedload(ReviewRequest.submitter),
            )
            .join(Document, ReviewRequest.document_id == Document.id)
            .filter(ReviewRequest.status == ReviewStatus.PENDING)
        )

        if actor.role != UserRole.SYSTEM_ADMIN:
            query = query.filter(Document.tenant_id == actor.tenant_id)

        return query.all()

    def _tenant_scope_for_review(self, review: ReviewRequest) -> int | None:
        return review.document.tenant_id if review.document else None

    def process_pending_reviews(
        self,
        *,
        actor: User,
        now: datetime | None = None,
        thresholds: ReviewSlaThresholds | None = None,
    ) -> ReviewSlaProcessResponse:
        effective_now = now or datetime.utcnow()
        effective_thresholds = thresholds or ReviewSlaThresholds(
            reminder_hours=settings.REVIEW_SLA_REMINDER_HOURS,
            escalation_hours=settings.REVIEW_SLA_ESCALATION_HOURS,
        )
        reminder_cutoff = effective_now - timedelta(hours=effective_thresholds.reminder_hours)
        escalation_cutoff = effective_now - timedelta(hours=effective_thresholds.escalation_hours)
        pending_reviews = self._pending_reviews(actor)

        items: list[ReviewSlaItem] = []
        reminders_sent = 0
        escalations_sent = 0

        for review in pending_reviews:
            reminder_recipient_ids: list[int] = []
            escalation_recipient_ids: list[int] = []
            reminder_sent = False
            escalation_sent = False
            exclude_user_ids = {review.submitted_by, actor.id}
            tenant_id = self._tenant_scope_for_review(review)

            if review.submitted_at <= reminder_cutoff and review.reviewer_reminded_at is None:
                reminder_recipients = self.notification_service.list_active_users_by_roles(
                    roles=[
                        UserRole.EDITOR,
                        UserRole.MANAGER,
                        UserRole.ADMIN,
                        UserRole.SYSTEM_ADMIN,
                    ],
                    tenant_id=tenant_id,
                    exclude_user_ids=exclude_user_ids,
                )
                for recipient in reminder_recipients:
                    self.notification_service.create_notification(
                        user_id=recipient.id,
                        notification_type=NotificationType.REVIEW_REMINDER,
                        title="Review reminder overdue",
                        message=(
                            f"Review #{review.id} for '{review.document.title}' has been pending "
                            f"for more than {effective_thresholds.reminder_hours} hours."
                        ),
                        link="/reviews",
                    )
                    reminder_recipient_ids.append(recipient.id)

                if reminder_recipient_ids:
                    review.reviewer_reminded_at = effective_now
                    reminder_sent = True
                    reminders_sent += 1

            if review.submitted_at <= escalation_cutoff and review.manager_escalated_at is None:
                escalation_recipients = self.notification_service.list_active_users_by_roles(
                    roles=[
                        UserRole.MANAGER,
                        UserRole.ADMIN,
                        UserRole.SYSTEM_ADMIN,
                    ],
                    tenant_id=tenant_id,
                    exclude_user_ids=exclude_user_ids,
                )
                for recipient in escalation_recipients:
                    self.notification_service.create_notification(
                        user_id=recipient.id,
                        notification_type=NotificationType.REVIEW_ESCALATED,
                        title="Review escalation required",
                        message=(
                            f"Review #{review.id} for '{review.document.title}' has been pending "
                            f"for more than {effective_thresholds.escalation_hours} hours."
                        ),
                        link="/reviews",
                    )
                    escalation_recipient_ids.append(recipient.id)

                if escalation_recipient_ids:
                    review.manager_escalated_at = effective_now
                    escalation_sent = True
                    escalations_sent += 1

            if reminder_sent or escalation_sent:
                items.append(
                    ReviewSlaItem(
                        review_id=review.id,
                        document_id=review.document_id,
                        reminder_sent=reminder_sent,
                        escalation_sent=escalation_sent,
                        reminder_recipient_ids=reminder_recipient_ids,
                        escalation_recipient_ids=escalation_recipient_ids,
                    )
                )

        self.db.commit()

        return ReviewSlaProcessResponse(
            processed_at=effective_now,
            reminder_threshold_hours=effective_thresholds.reminder_hours,
            escalation_threshold_hours=effective_thresholds.escalation_hours,
            reviews_scanned=len(pending_reviews),
            reminders_sent=reminders_sent,
            escalations_sent=escalations_sent,
            items=items,
        )
