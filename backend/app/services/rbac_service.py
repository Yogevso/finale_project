"""RBAC policy service and ACL publishing"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Iterable, Set

from sqlalchemy.orm import Session

from app.models import RbacPolicy, UserRole
from app.services.permissions import Permission, set_dynamic_role_permissions


class RbacService:
    """Service for RBAC policy persistence and publishing"""

    @staticmethod
    def get_policies(
        db: Session, include_inactive: bool = False
    ) -> Dict[UserRole, Set[Permission]]:
        query = db.query(RbacPolicy)
        if not include_inactive:
            query = query.filter(RbacPolicy.is_active.is_(True))
        policies = {}
        for row in query.all():
            policies[row.role] = RbacService._decode_permissions(row.permissions)
        return policies

    @staticmethod
    def upsert_policies(
        db: Session,
        policies: Dict[UserRole, Iterable[Permission]],
        updated_by: int | None,
    ) -> None:
        now = datetime.utcnow()
        for role, permissions in policies.items():
            encoded = json.dumps([p.value for p in permissions])
            row = db.query(RbacPolicy).filter(RbacPolicy.role == role).first()
            if row:
                row.permissions = encoded
                row.updated_by = updated_by
                row.is_active = True
                row.published_at = now
            else:
                row = RbacPolicy(
                    role=role,
                    permissions=encoded,
                    updated_by=updated_by,
                    is_active=True,
                    published_at=now,
                )
                db.add(row)
        db.commit()

    @staticmethod
    def publish_policies(db: Session) -> Dict[UserRole, Set[Permission]]:
        policies = RbacService.get_policies(db)
        set_dynamic_role_permissions(policies)
        return policies

    @staticmethod
    def _decode_permissions(raw: str) -> Set[Permission]:
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            values = []
        permissions: Set[Permission] = set()
        for value in values:
            try:
                permissions.add(Permission(value))
            except ValueError:
                continue
        return permissions
