"""Public API for the users bounded context."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.container import AppContainer, build_container
from app.dependencies.tenant import TenantContext
from app.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models import (
    AdminAction,
    Announcement,
    ApiKey,
    AssistantConversation,
    AssistantUploadedFile,
    Attachment,
    Bookmark,
    CannedResponse,
    ChangelogEntry,
    Chat,
    ChatMessage,
    ChatParticipant,
    CollaborationActivity,
    CollaborationSession,
    CollaborationSnapshot,
    Comment,
    DataRequest,
    Document,
    DocumentWatcher,
    Experiment,
    ExperimentAssignment,
    FeatureFlag,
    Feedback,
    ImpersonationSession,
    Invitation,
    InvitationStatus,
    MaintenanceWindow,
    Notification,
    NotificationType,
    PasswordReset,
    RbacPolicy,
    ReadingProgress,
    ReviewRequest,
    ReviewStatus,
    SavedSearch,
    SecurityEvent,
    SupportTicket,
    SupportTicketAssignment,
    SupportTicketMessage,
    SystemSetting,
    Tenant,
    TenantQuota,
    User,
    UserRole,
    UserSession,
    Version,
    WebhookRegistration,
    document_company_assignments,
)
from app.repositories import UserRepository
from app.schemas import UserCreate, UserUpdate
from app.security import get_password_hash

logger = logging.getLogger(__name__)
_USER_CREATE_CONFLICT_DETAIL = "A user with that email or username already exists"


class UsersContextAPI:
    """Stable context-level API for user management orchestration."""

    ROLE_HIERARCHY = {
        UserRole.SYSTEM_ADMIN: 6,
        UserRole.ADMIN: 5,
        UserRole.MANAGER: 4,
        UserRole.EDITOR: 3,
        UserRole.VIEWER: 2,
        UserRole.CUSTOMER: 1,
    }

    def __init__(self, container: AppContainer | None = None) -> None:
        self.container = container or build_container()

    def _auth_service(self, db: Session):
        return self.container.auth_service(db)

    @staticmethod
    def _user_repository(db: Session) -> UserRepository:
        return UserRepository(db)

    @staticmethod
    def _validation_error(message: str, *, error_code: str | None = None) -> ValidationError:
        headers = {"X-Error-Code": error_code} if error_code else None
        return ValidationError(message, error_code=error_code, headers=headers)

    @staticmethod
    def _admin_access_required() -> PermissionDeniedError:
        return PermissionDeniedError("Admin access required")

    def _get_user_for_delete(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> User:
        user = self._user_repository(db).get_by_id_with_tenant(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise NotFoundError("User not found")

        if user.id == current_user.id:
            raise ValidationError("You cannot delete yourself")

        if not self._can_manage_role(current_user.role, user.role):
            raise PermissionDeniedError("Cannot delete users with higher roles")

        return user

    def _ensure_user_can_be_deactivated(self, *, user: User, db: Session) -> None:
        user_repository = self._user_repository(db)
        if user.role == UserRole.SYSTEM_ADMIN:
            system_admin_count = user_repository.count_other_active_system_admins(
                exclude_user_id=user.id
            )
            if system_admin_count == 0:
                raise self._validation_error(
                    "Cannot deactivate the last active system admin",
                    error_code="last_system_admin",
                )
        elif user.role == UserRole.ADMIN and user.tenant_id:
            admin_count = user_repository.count_other_active_company_admins(
                tenant_id=user.tenant_id,
                exclude_user_id=user.id,
            )
            if admin_count == 0:
                raise self._validation_error(
                    "Cannot deactivate the last admin for this company",
                    error_code="last_company_admin",
                )

    def _cascade_user_deactivation(self, *, user: User, db: Session) -> None:
        db.query(Invitation).filter(
            Invitation.invited_by == user.id,
            Invitation.status == InvitationStatus.PENDING,
        ).update({"status": InvitationStatus.CANCELLED})
        self._cancel_pending_reviews_for_user(user=user, db=db)
        self._auth_service(db).revoke_all_user_sessions(user.id, commit=False)

    def _cancel_pending_reviews_for_user(self, *, user: User, db: Session) -> None:
        """Cancel all pending reviews where this user is the reviewer."""
        db.query(ReviewRequest).filter(
            ReviewRequest.reviewed_by == user.id,
            ReviewRequest.status == ReviewStatus.PENDING,
        ).update({"status": ReviewStatus.CANCELLED})

    @staticmethod
    def _build_hard_delete_blocker_message(blockers: list[str]) -> str:
        preview = ", ".join(blockers[:4])
        if len(blockers) > 4:
            preview = f"{preview}, and {len(blockers) - 4} more"
        return (
            "Cannot permanently delete user because they still own preserved records in: "
            f"{preview}. Reassign or remove those records first."
        )

    def _collect_hard_delete_blockers(
        self,
        *,
        user: User,
        db: Session,
        chat_db: Session | None,
    ) -> list[str]:
        blockers: list[str] = []
        blocker_checks = [
            ("documents", db.query(Document.id).filter(Document.created_by == user.id)),
            ("versions", db.query(Version.id).filter(Version.created_by == user.id)),
            ("attachments", db.query(Attachment.id).filter(Attachment.uploaded_by == user.id)),
            ("comments", db.query(Comment.id).filter(Comment.user_id == user.id)),
            ("feedback", db.query(Feedback.id).filter(Feedback.user_id == user.id)),
            (
                "review submissions",
                db.query(ReviewRequest.id).filter(ReviewRequest.submitted_by == user.id),
            ),
            (
                "support tickets",
                db.query(SupportTicket.id).filter(SupportTicket.customer_id == user.id),
            ),
            (
                "support messages",
                db.query(SupportTicketMessage.id).filter(SupportTicketMessage.sender_id == user.id),
            ),
            ("admin actions", db.query(AdminAction.id).filter(AdminAction.requested_by == user.id)),
            ("data requests", db.query(DataRequest.id).filter(DataRequest.user_id == user.id)),
        ]

        for label, query in blocker_checks:
            if query.first() is not None:
                blockers.append(label)

        if chat_db is None:
            return blockers

        chat_blocker_checks = [
            ("owned chats", chat_db.query(Chat.id).filter(Chat.created_by == user.id)),
            (
                "chat participation",
                chat_db.query(ChatParticipant.id).filter(ChatParticipant.user_id == user.id),
            ),
            (
                "chat messages",
                chat_db.query(ChatMessage.id).filter(ChatMessage.sender_id == user.id),
            ),
        ]
        for label, query in chat_blocker_checks:
            if query.first() is not None:
                blockers.append(label)

        return blockers

    def _purge_hard_delete_core_dependencies(
        self,
        *,
        user: User,
        replacement_user_id: int,
        db: Session,
    ) -> None:
        db.query(Invitation).filter(Invitation.created_user_id == user.id).update(
            {Invitation.created_user_id: None},
            synchronize_session=False,
        )
        db.query(Invitation).filter(Invitation.invited_by == user.id).update(
            {Invitation.invited_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(ReviewRequest).filter(ReviewRequest.reviewed_by == user.id).update(
            {ReviewRequest.reviewed_by: None},
            synchronize_session=False,
        )
        db.query(Feedback).filter(Feedback.responded_by == user.id).update(
            {Feedback.responded_by: None},
            synchronize_session=False,
        )
        db.query(Version).filter(Version.published_by == user.id).update(
            {Version.published_by: None},
            synchronize_session=False,
        )
        db.query(SystemSetting).filter(SystemSetting.updated_by == user.id).update(
            {SystemSetting.updated_by: None},
            synchronize_session=False,
        )
        db.query(RbacPolicy).filter(RbacPolicy.updated_by == user.id).update(
            {RbacPolicy.updated_by: None},
            synchronize_session=False,
        )
        db.query(TenantQuota).filter(TenantQuota.updated_by == user.id).update(
            {TenantQuota.updated_by: None},
            synchronize_session=False,
        )
        db.query(FeatureFlag).filter(FeatureFlag.updated_by == user.id).update(
            {FeatureFlag.updated_by: None},
            synchronize_session=False,
        )
        db.query(AdminAction).filter(AdminAction.reviewed_by == user.id).update(
            {AdminAction.reviewed_by: None},
            synchronize_session=False,
        )
        db.query(Announcement).filter(Announcement.created_by == user.id).update(
            {Announcement.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(ChangelogEntry).filter(ChangelogEntry.created_by == user.id).update(
            {ChangelogEntry.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(CannedResponse).filter(CannedResponse.created_by == user.id).update(
            {CannedResponse.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(SupportTicketAssignment).filter(
            SupportTicketAssignment.agent_id == user.id
        ).delete(synchronize_session=False)
        db.query(ApiKey).filter(ApiKey.user_id == user.id).delete(synchronize_session=False)
        db.query(Experiment).filter(Experiment.created_by == user.id).update(
            {Experiment.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(ExperimentAssignment).filter(ExperimentAssignment.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(ImpersonationSession).filter(ImpersonationSession.admin_user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(WebhookRegistration).filter(WebhookRegistration.created_by == user.id).update(
            {WebhookRegistration.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(MaintenanceWindow).filter(MaintenanceWindow.created_by == user.id).update(
            {MaintenanceWindow.created_by: replacement_user_id},
            synchronize_session=False,
        )
        db.query(UserSession).filter(UserSession.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(SavedSearch).filter(SavedSearch.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(Bookmark).filter(Bookmark.user_id == user.id).delete(synchronize_session=False)
        db.query(DocumentWatcher).filter(DocumentWatcher.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(ReadingProgress).filter(ReadingProgress.user_id == user.id).delete(
            synchronize_session=False
        )
        db.execute(
            document_company_assignments.update()
            .where(document_company_assignments.c.assigned_by == user.id)
            .values(assigned_by=None)
        )

    @staticmethod
    def _purge_hard_delete_chat_dependencies(*, user_id: int, chat_db: Session) -> None:
        chat_db.query(Notification).filter(Notification.user_id == user_id).delete(
            synchronize_session=False
        )
        chat_db.query(AssistantUploadedFile).filter(
            AssistantUploadedFile.user_id == user_id
        ).delete(synchronize_session=False)
        chat_db.query(AssistantConversation).filter(
            AssistantConversation.user_id == user_id
        ).delete(synchronize_session=False)
        chat_db.query(CollaborationSession).filter(CollaborationSession.user_id == user_id).delete(
            synchronize_session=False
        )
        chat_db.query(CollaborationActivity).filter(
            CollaborationActivity.user_id == user_id
        ).delete(synchronize_session=False)
        chat_db.query(CollaborationSnapshot).filter(
            CollaborationSnapshot.created_by == user_id
        ).update({CollaborationSnapshot.created_by: None}, synchronize_session=False)

    @staticmethod
    def _role_label(role: UserRole) -> str:
        return role.value.replace("_", " ")

    def _notify_role_change(
        self,
        *,
        user: User,
        old_role: UserRole,
        chat_db: Session | None,
    ) -> None:
        if chat_db is None:
            return

        chat_db.add(
            Notification(
                user_id=user.id,
                type=NotificationType.SYSTEM,
                title="Your access role changed",
                message=(
                    f"Your role changed from {self._role_label(old_role)} "
                    f"to {self._role_label(user.role)}. Reload or sign in again "
                    "to apply the updated permissions."
                ),
                link="/profile",
            )
        )
        try:
            chat_db.commit()
        except Exception:  # policy: BOUNDARY — user context surfaces a stable failure contract
            chat_db.rollback()
            logger.exception("Failed to persist role-change notification for user_id=%s", user.id)

    def list_users(
        self,
        *,
        role: Optional[UserRole],
        company_id: Optional[int],
        is_active: Optional[bool],
        search: Optional[str],
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> list[dict[str, object]]:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
            raise self._admin_access_required()

        users = self._user_repository(db).list_for_management(
            tenant_id=tenant_ctx.tenant_id,
            is_system_admin=tenant_ctx.is_system_admin,
            role=role,
            company_id=company_id,
            is_active=is_active,
            search=search,
        )
        return [self._serialize_user(user, db) for user in users]

    def create_user(
        self,
        *,
        user_data: UserCreate,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        user_repository = self._user_repository(db)
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
            raise self._admin_access_required()

        if not self._can_manage_role(current_user.role, user_data.role):
            raise PermissionDeniedError(
                f"You cannot create users with role '{user_data.role.value}'"
            )

        target_tenant_id = (
            user_data.tenant_id if user_data.tenant_id is not None else tenant_ctx.tenant_id
        )

        if user_data.role == UserRole.CUSTOMER and not target_tenant_id:
            raise ValidationError("Customers must be assigned to a company")

        if target_tenant_id is not None:
            tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
            if not tenant:
                raise NotFoundError("Company not found")
            if not tenant_ctx.is_system_admin and tenant.id != tenant_ctx.tenant_id:
                raise PermissionDeniedError("Cannot assign users to other companies")

        if user_repository.get_by_email(user_data.email):
            raise ValidationError(_USER_CREATE_CONFLICT_DETAIL)
        if user_repository.get_by_username(user_data.username):
            raise ValidationError(_USER_CREATE_CONFLICT_DETAIL)

        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            tenant_id=target_tenant_id,
            is_active=True,
            is_email_verified=False,
        )
        db.add(user)
        db.flush()

        db.add(
            SecurityEvent(
                user_id=current_user.id,
                event_type="user_created",
            )
        )

        db.commit()
        db.refresh(user)
        return self._serialize_user(user, db)

    def get_user(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        user = self._user_repository(db).get_by_id_with_tenant(user_id)
        if not user:
            raise NotFoundError("User not found")

        if user.id != current_user.id:
            if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
                raise self._admin_access_required()
            if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
                raise NotFoundError("User not found")

        return self._serialize_user(user, db)

    def update_user(
        self,
        *,
        user_id: int,
        user_data: UserUpdate,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
        chat_db: Session | None = None,
    ) -> dict[str, object]:
        user_repository = self._user_repository(db)
        user = user_repository.get_by_id_with_tenant(user_id)
        if not user:
            raise NotFoundError("User not found")

        is_self = user.id == current_user.id
        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]
        tenant_id_provided = "tenant_id" in user_data.model_fields_set
        has_privileged_update = (
            user_data.role is not None or user_data.is_active is not None or tenant_id_provided
        )

        old_role = user.role
        old_is_active = user.is_active
        should_revoke_sessions = False
        deactivation_cascade_applied = False

        if not is_self and not is_admin:
            raise self._admin_access_required()
        if has_privileged_update and not is_admin:
            raise self._admin_access_required()

        if (
            not is_self
            and not tenant_ctx.is_system_admin
            and user.tenant_id != tenant_ctx.tenant_id
        ):
            raise NotFoundError("User not found")

        if is_admin and not is_self and not self._can_manage_role(current_user.role, user.role):
            raise PermissionDeniedError("Cannot modify users with higher roles")

        if user_data.email is not None:
            existing = user_repository.get_by_email_excluding(user_data.email, user_id)
            if existing:
                raise ValidationError("Email already registered")
            user.email = user_data.email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        if user_data.role is not None:
            if not self._can_manage_role(current_user.role, user_data.role):
                raise PermissionDeniedError(f"You cannot assign role '{user_data.role.value}'")
            if is_self and self.ROLE_HIERARCHY.get(user_data.role, 0) < self.ROLE_HIERARCHY.get(
                user.role, 0
            ):
                raise ValidationError("You cannot demote yourself")

            is_downgrade = self.ROLE_HIERARCHY.get(user_data.role, 0) < self.ROLE_HIERARCHY.get(
                user.role, 0
            )
            if is_downgrade:
                if user.role == UserRole.SYSTEM_ADMIN:
                    system_admin_count = user_repository.count_other_active_system_admins(
                        exclude_user_id=user.id
                    )
                    if system_admin_count == 0:
                        raise self._validation_error(
                            "Cannot downgrade the last active system admin",
                            error_code="last_system_admin",
                        )
                elif user.role == UserRole.ADMIN and user.tenant_id:
                    admin_count = user_repository.count_other_active_company_admins(
                        tenant_id=user.tenant_id,
                        exclude_user_id=user.id,
                    )
                    if admin_count == 0:
                        raise self._validation_error(
                            "Cannot downgrade the last admin for this company",
                            error_code="last_company_admin",
                        )

            user.role = user_data.role

        if user_data.is_active is not None:
            if is_self and not user_data.is_active:
                raise ValidationError("You cannot deactivate yourself")

            was_active = user.is_active
            is_deactivating = not user_data.is_active and was_active

            if is_deactivating:
                self._ensure_user_can_be_deactivated(user=user, db=db)
                self._cascade_user_deactivation(user=user, db=db)
                should_revoke_sessions = True
                deactivation_cascade_applied = True

            is_reactivating = user_data.is_active and not was_active
            if is_reactivating and user.role == UserRole.CUSTOMER and user.tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                if not tenant:
                    raise self._validation_error(
                        "Cannot reactivate user: their company no longer exists",
                        error_code="user_company_deleted",
                    )
                if not tenant.is_active:
                    raise self._validation_error(
                        "Cannot reactivate user: their company is deactivated",
                        error_code="user_company_inactive",
                    )

            user.is_active = user_data.is_active

        if tenant_id_provided:
            requested_tenant_id = user_data.tenant_id
            if user.role == UserRole.CUSTOMER and not requested_tenant_id:
                raise ValidationError("Customers must be assigned to a company")
            if requested_tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == requested_tenant_id).first()
                if not tenant:
                    raise NotFoundError("Company not found")
                if not tenant.is_active:
                    raise self._validation_error(
                        "Cannot assign user to a deactivated company",
                        error_code="company_inactive",
                    )
                if not tenant_ctx.is_system_admin and requested_tenant_id != tenant_ctx.tenant_id:
                    raise PermissionDeniedError("Cannot assign users to other companies")
            elif not tenant_ctx.is_system_admin:
                raise PermissionDeniedError("Cannot remove company assignment in this tenant scope")
            user.tenant_id = requested_tenant_id

        if user.role == UserRole.CUSTOMER and not user.tenant_id:
            raise ValidationError("Customers must be assigned to a company")

        if user.is_active and user.role == UserRole.CUSTOMER and user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if not tenant:
                raise self._validation_error(
                    "Cannot assign customer role: company no longer exists",
                    error_code="role_change_company_deleted",
                )
            if not tenant.is_active:
                raise self._validation_error(
                    "Cannot assign customer role: company is deactivated",
                    error_code="role_change_company_inactive",
                )

        if user.role != old_role:
            should_revoke_sessions = True
            is_demotion = self.ROLE_HIERARCHY.get(user.role, 0) < self.ROLE_HIERARCHY.get(
                old_role, 0
            )
            if is_demotion:
                self._cancel_pending_reviews_for_user(user=user, db=db)

        if should_revoke_sessions and not deactivation_cascade_applied:
            self._auth_service(db).revoke_all_user_sessions(user.id, commit=False)

        if user.role != old_role:
            db.add(
                SecurityEvent(
                    user_id=current_user.id,
                    event_type="user_role_changed",
                )
            )
        if user.is_active != old_is_active:
            event_type = "user_deactivated" if not user.is_active else "user_reactivated"
            db.add(
                SecurityEvent(
                    user_id=current_user.id,
                    event_type=event_type,
                )
            )

        db.commit()
        db.refresh(user)
        if user.role != old_role:
            self._notify_role_change(user=user, old_role=old_role, chat_db=chat_db)
        return self._serialize_user(user, db)

    def delete_user(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> None:
        if current_user.role not in [UserRole.ADMIN, UserRole.SYSTEM_ADMIN]:
            raise self._admin_access_required()

        user = self._get_user_for_delete(
            user_id=user_id,
            current_user=current_user,
            tenant_ctx=tenant_ctx,
            db=db,
        )

        if user.is_active:
            self._ensure_user_can_be_deactivated(user=user, db=db)

        self._cascade_user_deactivation(user=user, db=db)
        user.is_active = False

        db.add(
            SecurityEvent(
                user_id=current_user.id,
                event_type="user_deleted",
            )
        )

        db.commit()

    def hard_delete_user(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
        chat_db: Session | None = None,
    ) -> None:
        if current_user.role != UserRole.SYSTEM_ADMIN:
            raise PermissionDeniedError("Only system administrators can permanently delete users")

        user = self._get_user_for_delete(
            user_id=user_id,
            current_user=current_user,
            tenant_ctx=tenant_ctx,
            db=db,
        )

        if user.is_active:
            raise self._validation_error(
                "Deactivate the user before permanent deletion",
                error_code="user_must_be_deactivated_first",
            )

        blockers = self._collect_hard_delete_blockers(user=user, db=db, chat_db=chat_db)
        if blockers:
            raise ConflictError(
                self._build_hard_delete_blocker_message(blockers),
                error_code="user_hard_delete_blocked",
            )

        self._cascade_user_deactivation(user=user, db=db)
        self._purge_hard_delete_core_dependencies(
            user=user,
            replacement_user_id=current_user.id,
            db=db,
        )
        if chat_db is db:
            self._purge_hard_delete_chat_dependencies(user_id=user_id, chat_db=chat_db)
        db.delete(user)
        db.add(
            SecurityEvent(
                user_id=current_user.id,
                event_type="user_hard_deleted",
            )
        )
        db.commit()

        if chat_db is None or chat_db is db:
            return

        try:
            self._purge_hard_delete_chat_dependencies(user_id=user_id, chat_db=chat_db)
            chat_db.commit()
        except (
            Exception
        ):  # policy: BOUNDARY — hard delete succeeded in core DB; chat cleanup is best-effort
            chat_db.rollback()
            logger.exception("Failed to purge chat-side data for hard-deleted user_id=%s", user_id)

    def check_company_binding(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        """Check a user's company binding status."""
        user = self._user_repository(db).get_by_id_with_tenant(user_id)
        if not user:
            raise NotFoundError("User not found")

        is_self = user.id == current_user.id
        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]
        if not is_self and not is_admin:
            raise PermissionDeniedError("Access denied")

        if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise NotFoundError("User not found")

        is_customer = user.role == UserRole.CUSTOMER
        requires_company = is_customer

        result: dict[str, object] = {
            "user_id": user.id,
            "role": user.role.value,
            "is_customer": is_customer,
            "requires_company": requires_company,
            "has_company": user.tenant_id is not None,
            "company_id": user.tenant_id,
            "company_name": None,
            "company_slug": None,
            "company_is_active": None,
            "binding_valid": True,
            "binding_issues": [],
        }

        issues = []

        if user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                result["company_name"] = tenant.name
                result["company_slug"] = tenant.slug
                result["company_is_active"] = tenant.is_active
                if not tenant.is_active:
                    issues.append("Company is deactivated")
            else:
                result["company_is_active"] = False
                issues.append("Company no longer exists")
        elif requires_company:
            issues.append("Customer user must be bound to a company")

        result["binding_issues"] = issues
        result["binding_valid"] = len(issues) == 0

        return result

    @classmethod
    def can_manage_role(cls, manager_role: UserRole, target_role: UserRole) -> bool:
        return cls._can_manage_role(manager_role, target_role)

    @classmethod
    def _can_manage_role(cls, manager_role: UserRole, target_role: UserRole) -> bool:
        if manager_role == UserRole.SYSTEM_ADMIN:
            return True
        if manager_role == UserRole.ADMIN:
            return target_role != UserRole.SYSTEM_ADMIN
        if manager_role == UserRole.MANAGER:
            return target_role in [UserRole.EDITOR, UserRole.VIEWER, UserRole.CUSTOMER]
        return False

    def serialize_user(self, user: User, db: Session) -> dict[str, object]:
        return self._serialize_user(user, db)

    @staticmethod
    def _serialize_user(user: User, db: Session) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "timezone": user.timezone or "UTC",
            "locale": user.locale or "en",
            "notification_preferences": user.notification_preferences or {},
            "avatar_url": user.avatar_url,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "company_name": None,
            "company_slug": None,
        }
        if user.tenant_id:
            tenant = (
                getattr(user, "tenant", None)
                or db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            )
            if tenant:
                payload["company_name"] = tenant.name
                payload["company_slug"] = tenant.slug
        return payload
