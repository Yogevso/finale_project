"""Audience-driven policy specifications for link-sharing and embedding.

These specifications encode the business rules governing which sharing and
embedding actions are permitted for each document visibility level.

Task 187: Link-sharing policy by audience type
Task 188: External embed audience restrictions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet

from app.models import Document, DocumentVisibility


class SharingAction(str, Enum):
    """Allowed link-sharing actions."""

    DIRECT_LINK = "direct_link"  # Shareable URL (always available)
    COPY_LINK = "copy_link"  # Copy-to-clipboard button
    EMAIL_LINK = "email_link"  # Share via email
    SOCIAL_SHARE = "social_share"  # Share on social media


class EmbedAction(str, Enum):
    """Allowed embed actions."""

    IFRAME = "iframe"  # Embeddable in an <iframe>
    OEMBED = "oembed"  # oEmbed auto-discovery
    API_EMBED = "api_embed"  # Programmatic API embed


# ---------------------------------------------------------------------------
# Audience-based sharing policy
# ---------------------------------------------------------------------------

_SHARING_RULES: dict[DocumentVisibility, frozenset[SharingAction]] = {
    DocumentVisibility.PUBLIC: frozenset(SharingAction),  # all actions
    DocumentVisibility.INTERNAL: frozenset(
        {SharingAction.DIRECT_LINK, SharingAction.COPY_LINK, SharingAction.EMAIL_LINK}
    ),
    DocumentVisibility.COMPANY: frozenset(
        {SharingAction.DIRECT_LINK, SharingAction.COPY_LINK}
    ),
}

_EMBED_RULES: dict[DocumentVisibility, frozenset[EmbedAction]] = {
    DocumentVisibility.PUBLIC: frozenset(EmbedAction),  # all actions
    DocumentVisibility.INTERNAL: frozenset({EmbedAction.API_EMBED}),
    DocumentVisibility.COMPANY: frozenset(),  # no external embedding
}


@dataclass(frozen=True)
class LinkSharingPolicySpec:
    """Determines which link-sharing actions are allowed for a document.

    Usage::

        spec = LinkSharingPolicySpec.for_document(document)
        if spec.is_action_allowed(SharingAction.SOCIAL_SHARE):
            ...
        allowed = spec.allowed_actions  # frozenset of SharingAction
    """

    visibility: DocumentVisibility
    allowed_actions: FrozenSet[SharingAction] = field(default_factory=frozenset)

    @classmethod
    def for_document(cls, document: Document) -> LinkSharingPolicySpec:
        """Build a policy from the document's current visibility."""
        visibility = document.visibility
        return cls(
            visibility=visibility,
            allowed_actions=_SHARING_RULES.get(visibility, frozenset()),
        )

    @classmethod
    def for_visibility(cls, visibility: DocumentVisibility) -> LinkSharingPolicySpec:
        """Build a policy from an explicit visibility value."""
        return cls(
            visibility=visibility,
            allowed_actions=_SHARING_RULES.get(visibility, frozenset()),
        )

    def is_action_allowed(self, action: SharingAction) -> bool:
        return action in self.allowed_actions

    def to_dict(self) -> dict:
        return {
            "visibility": self.visibility.value,
            "allowed_actions": sorted(a.value for a in self.allowed_actions),
            "social_share_enabled": SharingAction.SOCIAL_SHARE in self.allowed_actions,
            "email_share_enabled": SharingAction.EMAIL_LINK in self.allowed_actions,
        }


@dataclass(frozen=True)
class ExternalEmbedPolicySpec:
    """Determines which embed actions are allowed for a document.

    Usage::

        spec = ExternalEmbedPolicySpec.for_document(document)
        if spec.is_action_allowed(EmbedAction.IFRAME):
            ...
        x_frame = spec.x_frame_options_header  # "DENY" or "ALLOWALL"
    """

    visibility: DocumentVisibility
    allowed_actions: FrozenSet[EmbedAction] = field(default_factory=frozenset)

    @classmethod
    def for_document(cls, document: Document) -> ExternalEmbedPolicySpec:
        """Build a policy from the document's current visibility."""
        visibility = document.visibility
        return cls(
            visibility=visibility,
            allowed_actions=_EMBED_RULES.get(visibility, frozenset()),
        )

    @classmethod
    def for_visibility(cls, visibility: DocumentVisibility) -> ExternalEmbedPolicySpec:
        """Build a policy from an explicit visibility value."""
        return cls(
            visibility=visibility,
            allowed_actions=_EMBED_RULES.get(visibility, frozenset()),
        )

    def is_action_allowed(self, action: EmbedAction) -> bool:
        return action in self.allowed_actions

    @property
    def x_frame_options_header(self) -> str:
        """Return the X-Frame-Options header value for this policy."""
        if EmbedAction.IFRAME in self.allowed_actions:
            return "ALLOWALL"
        return "DENY"

    @property
    def content_security_policy_frame_ancestors(self) -> str:
        """Return the CSP frame-ancestors directive value."""
        if EmbedAction.IFRAME in self.allowed_actions:
            return "*"
        return "'none'"

    def to_dict(self) -> dict:
        return {
            "visibility": self.visibility.value,
            "allowed_actions": sorted(a.value for a in self.allowed_actions),
            "iframe_allowed": EmbedAction.IFRAME in self.allowed_actions,
            "oembed_allowed": EmbedAction.OEMBED in self.allowed_actions,
            "x_frame_options": self.x_frame_options_header,
        }
