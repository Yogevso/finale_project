"""Domain/application error hierarchy with transport-agnostic semantics."""

from __future__ import annotations

from fastapi import status


class DomainError(Exception):
    """Base class for expected business/domain failures."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "domain_error"

    def __init__(self, message: str, *, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code


class ValidationError(DomainError):
    """Input is syntactically valid but fails business validation."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "validation_error"


class AuthenticationError(DomainError):
    """Authentication context is missing/invalid for the requested operation."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"


class PermissionDeniedError(DomainError):
    """Caller is authenticated but lacks authorization to perform the operation."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"


class NotFoundError(DomainError):
    """Requested domain resource does not exist or is not visible to caller."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ConflictError(DomainError):
    """Requested operation conflicts with current domain state."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class InvalidStateError(DomainError):
    """Operation is not allowed for the current resource lifecycle state."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_state"


class PreconditionRequiredError(DomainError):
    """Caller omitted a required write precondition token."""

    status_code = status.HTTP_428_PRECONDITION_REQUIRED
    error_code = "precondition_required"

