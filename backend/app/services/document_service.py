"""Document Service"""
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import ActionType, AuditLog, Document, DocumentStatus, User, UserRole, Version
from app.schemas import DocumentCreate, DocumentUpdate


class DocumentService:
    """Document CRUD service with multi-tenancy support"""
    
    def __init__(self, db: Session, tenant_ctx: Optional[TenantContext] = None):
        self.db = db
        self.tenant_ctx = tenant_ctx
    
    def _base_query(self):
        """Base query with tenant filtering applied"""
        query = self.db.query(Document)
        
        if self.tenant_ctx and not self.tenant_ctx.is_super_admin:
            query = query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        
        return query
    
    def _verify_access(self, document: Document) -> None:
        """Verify current user can access this document"""
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if self.tenant_ctx and not self.tenant_ctx.is_super_admin:
            if document.tenant_id != self.tenant_ctx.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )

    def generate_document_number(self) -> str:
        """Generate unique document number (DOC-YYYYMMDD-XXXX)"""
        from datetime import datetime

        today = datetime.utcnow().strftime("%Y%m%d")
        prefix = f"DOC-{today}"

        # Get count of documents created today (tenant-scoped)
        count = self._base_query().filter(
            Document.document_number.like(f"{prefix}-%")
        ).count()

        return f"{prefix}-{count + 1:04d}"

    def create_document(self, document_data: DocumentCreate, user: User) -> Document:
        """Create a new document"""
        # Generate document number
        document_number = self.generate_document_number()
        
        # Get tenant_id from context or user
        tenant_id = None
        if self.tenant_ctx:
            tenant_id = self.tenant_ctx.tenant_id
        elif user.tenant_id:
            tenant_id = user.tenant_id

        # Create document
        document = Document(
            title=document_data.title,
            document_number=document_number,
            description=document_data.description,
            status=document_data.status,
            category=document_data.category,
            tags=document_data.tags,
            created_by=user.id,
            tenant_id=tenant_id
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        # Create initial version
        version = Version(
            document_id=document.id,
            version_number=1,
            content=document_data.description or "",
            changes_summary="Initial version",
            created_by=user.id
        )
        self.db.add(version)

        # Create audit log
        audit = AuditLog(
            user_id=user.id,
            document_id=document.id,
            action=ActionType.CREATE,
            details=f"Created document: {document.title}"
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(document)

        return document

    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID with tenant filtering"""
        document = self._base_query().filter(Document.id == document_id).first()
        return document

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """Get list of documents with filters, pagination, and tenant filtering"""
        query = self._base_query()

        # Apply filters
        if status:
            query = query.filter(Document.status == status)

        if category:
            query = query.filter(Document.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                    Document.document_number.ilike(search_pattern),
                    Document.tags.ilike(search_pattern)
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

        return documents, total

    def update_document(
        self,
        document_id: int,
        document_data: DocumentUpdate,
        user: User
    ) -> Document:
        """Update document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_access(document)

        # Track changes
        changes = []

        # Update fields
        if document_data.title is not None:
            if document.title != document_data.title:
                changes.append(f"Title changed from '{document.title}' to '{document_data.title}'")
            document.title = document_data.title

        if document_data.description is not None:
            document.description = document_data.description

        if document_data.status is not None:
            if document.status != document_data.status:
                changes.append(f"Status changed from '{document.status.value}' to '{document_data.status.value}'")
            document.status = document_data.status

        if document_data.category is not None:
            document.category = document_data.category

        if document_data.tags is not None:
            document.tags = document_data.tags

        # Create new version if there are changes
        if changes:
            latest_version = self.db.query(Version).filter(
                Version.document_id == document_id
            ).order_by(Version.version_number.desc()).first()

            new_version_number = (latest_version.version_number + 1) if latest_version else 1

            version = Version(
                document_id=document.id,
                version_number=new_version_number,
                content=document.description or "",
                changes_summary="; ".join(changes),
                created_by=user.id
            )
            self.db.add(version)

        # Create audit log
        audit = AuditLog(
            user_id=user.id,
            document_id=document.id,
            action=ActionType.UPDATE,
            details="; ".join(changes) if changes else "Document updated"
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(document)

        return document

    def delete_document(self, document_id: int, user: User) -> None:
        """Delete document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_access(document)

        # Create audit log before deletion
        audit = AuditLog(
            user_id=user.id,
            document_id=document.id,
            action=ActionType.DELETE,
            details=f"Deleted document: {document.title}"
        )
        self.db.add(audit)
        self.db.commit()

        # Delete document (cascade will delete versions, attachments, comments)
        self.db.delete(document)
        self.db.commit()
