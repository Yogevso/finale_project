"""Tenant context middleware for request-scoped tenant isolation.

This middleware extracts the current user's tenant_id and injects it into
the request state, making it available for downstream handlers and services.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for tenant ID - accessible across async boundaries
_current_tenant_id: ContextVar[Optional[int]] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> Optional[int]:
    """Get the current tenant ID from request context.
    
    Returns None if:
    - No tenant context is set (anonymous request)
    - User is a system admin (no tenant scope)
    - Request is outside the middleware chain
    """
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: Optional[int]) -> None:
    """Set the current tenant ID in request context.
    
    Called by the middleware after extracting tenant from authenticated user.
    """
    _current_tenant_id.set(tenant_id)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts and propagates tenant context.
    
    On each request with an authenticated user:
    1. Extracts tenant_id from the user (set during auth dependency)
    2. Stores it in a context variable for the request duration
    3. Makes it available via get_current_tenant_id()
    
    This enables defensive programming patterns where services can
    verify they're operating within the correct tenant scope.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reset tenant context at start of each request
        set_current_tenant_id(None)
        
        # Tenant ID is typically set by auth dependencies after this middleware runs
        # We store a reference in request.state for later extraction
        request.state.tenant_context_set = False
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Clean up context after request completes
            set_current_tenant_id(None)


def inject_tenant_context(user) -> None:
    """Inject tenant context after user authentication.
    
    Called by auth dependencies after resolving the current user.
    This bridges the auth layer with the tenant context system.
    """
    if user is None:
        set_current_tenant_id(None)
        return
        
    tenant_id = getattr(user, "tenant_id", None)
    set_current_tenant_id(tenant_id)
    
    if tenant_id is not None:
        logger.debug("Tenant context set: tenant_id=%d, user_id=%d", tenant_id, user.id)


def require_tenant_match(document_tenant_id: Optional[int]) -> bool:
    """Verify the document's tenant matches the current request context.
    
    Returns True if:
    - Current user has no tenant (system admin or unscoped)
    - Document has no tenant (global document)
    - Both tenant IDs match
    
    Returns False if there's a tenant mismatch (cross-tenant access attempt).
    
    Usage in services:
        if not require_tenant_match(document.tenant_id):
            raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    """
    current_tenant = get_current_tenant_id()
    
    # System admins and unscoped users can access any tenant
    if current_tenant is None:
        return True
    
    # Global documents (no tenant) are accessible to all
    if document_tenant_id is None:
        return True
    
    # Must be same tenant
    return current_tenant == document_tenant_id
