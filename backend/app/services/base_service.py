"""Common service base classes."""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Query, Session

from app.dependencies.tenant import TenantContext
from app.models import Base

T = TypeVar("T", bound=Base)


class SessionService:
    """Base class for services with constructor-injected DB session."""

    def __init__(self, db: Session):
        self.db = db


class TenantAwareService(SessionService, Generic[T]):
    """
    Base class for services that need tenant isolation.

    Automatically filters queries by tenant_id unless:
    - User is SYSTEM_ADMIN
    - Service is explicitly used in unscoped mode
    """

    model: Type[T]

    def __init__(self, db: Session, tenant_ctx: Optional[TenantContext] = None):
        super().__init__(db)
        self.tenant_ctx = tenant_ctx

    def _base_query(self, model: Optional[Type[T]] = None) -> Query:
        """
        Create a base query with tenant filtering applied.

        If tenant_ctx is provided and user is not system_admin,
        the query will be filtered by tenant_id.
        """
        target_model = model or self.model
        query = self.db.query(target_model)

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            if hasattr(target_model, "tenant_id"):
                query = query.filter(target_model.tenant_id == self.tenant_ctx.tenant_id)

        return query

    def get_by_id(self, id: int, model: Optional[Type[T]] = None) -> Optional[T]:
        """Get a single record by ID with tenant filtering."""
        target_model = model or self.model
        return self._base_query(model).filter(target_model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100, model: Optional[Type[T]] = None) -> List[T]:
        """Get all records with tenant filtering."""
        return self._base_query(model).offset(skip).limit(limit).all()

    def count(self, model: Optional[Type[T]] = None) -> int:
        """Count records with tenant filtering."""
        return self._base_query(model).count()

    def create(self, obj: T) -> T:
        """Create a new record with automatic tenant assignment."""
        if self.tenant_ctx and hasattr(obj, "tenant_id") and obj.tenant_id is None:
            obj.tenant_id = self.tenant_ctx.tenant_id

        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: T) -> T:
        """Update an existing record."""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """Delete a record."""
        self.db.delete(obj)
        self.db.commit()

    def verify_tenant_access(self, obj: T) -> bool:
        """
        Verify that the current user can access this object.

        Returns True if:
        - User is SYSTEM_ADMIN
        - Object belongs to user's tenant
        - Object has no tenant (legacy/unassigned)
        """
        if not self.tenant_ctx:
            return True

        if self.tenant_ctx.is_system_admin:
            return True

        if not hasattr(obj, "tenant_id"):
            return True

        if obj.tenant_id is None:
            return True

        return obj.tenant_id == self.tenant_ctx.tenant_id
