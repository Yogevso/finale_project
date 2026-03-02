"""Tests for link-sharing and embed audience policies (Tasks 187-188)."""

from app.domain.specifications.audience_policies import (
    EmbedAction,
    ExternalEmbedPolicySpec,
    LinkSharingPolicySpec,
    SharingAction,
)
from app.models import DocumentVisibility


class TestLinkSharingPolicy:
    """Task 187: Link-sharing policy by audience type."""

    def test_public_allows_all_sharing_actions(self):
        spec = LinkSharingPolicySpec.for_visibility(DocumentVisibility.PUBLIC)
        for action in SharingAction:
            assert spec.is_action_allowed(action), f"{action} should be allowed for PUBLIC"

    def test_internal_disallows_social_share(self):
        spec = LinkSharingPolicySpec.for_visibility(DocumentVisibility.INTERNAL)
        assert spec.is_action_allowed(SharingAction.DIRECT_LINK)
        assert spec.is_action_allowed(SharingAction.COPY_LINK)
        assert spec.is_action_allowed(SharingAction.EMAIL_LINK)
        assert not spec.is_action_allowed(SharingAction.SOCIAL_SHARE)

    def test_company_allows_only_direct_and_copy(self):
        spec = LinkSharingPolicySpec.for_visibility(DocumentVisibility.COMPANY)
        assert spec.is_action_allowed(SharingAction.DIRECT_LINK)
        assert spec.is_action_allowed(SharingAction.COPY_LINK)
        assert not spec.is_action_allowed(SharingAction.EMAIL_LINK)
        assert not spec.is_action_allowed(SharingAction.SOCIAL_SHARE)

    def test_to_dict_includes_convenience_flags(self):
        policy = LinkSharingPolicySpec.for_visibility(DocumentVisibility.PUBLIC)
        d = policy.to_dict()
        assert d["visibility"] == "public"
        assert d["social_share_enabled"] is True
        assert d["email_share_enabled"] is True
        assert isinstance(d["allowed_actions"], list)


class TestExternalEmbedPolicy:
    """Task 188: External embed audience restrictions."""

    def test_public_allows_all_embed_actions(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.PUBLIC)
        for action in EmbedAction:
            assert spec.is_action_allowed(action), f"{action} should be allowed for PUBLIC"

    def test_internal_allows_only_api_embed(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.INTERNAL)
        assert spec.is_action_allowed(EmbedAction.API_EMBED)
        assert not spec.is_action_allowed(EmbedAction.IFRAME)
        assert not spec.is_action_allowed(EmbedAction.OEMBED)

    def test_company_disallows_all_embeds(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.COMPANY)
        for action in EmbedAction:
            assert not spec.is_action_allowed(action), f"{action} should NOT be allowed for COMPANY"

    def test_x_frame_options_public(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.PUBLIC)
        assert spec.x_frame_options_header == "ALLOWALL"

    def test_x_frame_options_internal(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.INTERNAL)
        assert spec.x_frame_options_header == "DENY"

    def test_x_frame_options_company(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.COMPANY)
        assert spec.x_frame_options_header == "DENY"

    def test_csp_frame_ancestors_public(self):
        spec = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.PUBLIC)
        assert spec.content_security_policy_frame_ancestors == "*"

    def test_to_dict_includes_convenience_flags(self):
        d = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.PUBLIC).to_dict()
        assert d["iframe_allowed"] is True
        assert d["oembed_allowed"] is True
        d2 = ExternalEmbedPolicySpec.for_visibility(DocumentVisibility.COMPANY).to_dict()
        assert d2["iframe_allowed"] is False
        assert d2["oembed_allowed"] is False


class TestPublicDocumentDetailIncludesPolicies:
    """Integration: public detail endpoint includes sharing + embed policies."""

    def test_public_detail_has_sharing_and_embed_policy(self, client, public_document):
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()
        assert "sharing_policy" in data
        assert data["sharing_policy"]["visibility"] == "public"
        assert "social_share" in data["sharing_policy"]["allowed_actions"]
        assert "embed_policy" in data
        assert data["embed_policy"]["iframe_allowed"] is True

    def test_public_detail_has_x_frame_options_header(self, client, public_document):
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        xfo = response.headers.get("x-frame-options", "")
        assert xfo == "ALLOWALL"
