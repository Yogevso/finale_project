"""Public API for tenant context operations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Tenant


@dataclass
class TenantsContextAPI:
    """Stable API for tenant metadata reads used by other contexts."""

    db: Session

    def get_tenant(self, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def list_tenants(self) -> list[Tenant]:
        return self.db.query(Tenant).order_by(Tenant.name.asc()).all()

