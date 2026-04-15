"""Tests for domain value objects introduced in Task 54."""

import pytest

from app.domain.value_objects import DocumentNumber, SemanticVersion, TopicSlug
from app.models import VersionBumpType


def test_document_number_formats_with_padded_suffix():
    value = DocumentNumber.from_date_key("20260227", 12)

    assert value.prefix == "DOC-20260227"
    assert str(value) == "DOC-20260227-0012"


def test_document_number_extract_sequence_suffix_for_matching_prefix():
    suffix = DocumentNumber.extract_sequence_suffix("DOC-20260227-0042", "DOC-20260227")

    assert suffix == 42


def test_document_number_extract_sequence_suffix_rejects_non_numeric_suffix():
    suffix = DocumentNumber.extract_sequence_suffix("DOC-20260227-ABCD", "DOC-20260227")

    assert suffix is None


def test_document_number_parse_rejects_noncanonical_shape():
    with pytest.raises(ValueError, match="Invalid document number format"):
        DocumentNumber.parse("DOC-TEST-0001")


def test_semantic_version_from_raw_parses_existing_value():
    value = SemanticVersion.from_raw("2.3.4", fallback_major=99)

    assert value.major == 2
    assert value.minor == 3
    assert value.patch == 4


def test_semantic_version_from_raw_falls_back_to_major_zero_patch():
    value = SemanticVersion.from_raw("not-semver", fallback_major=7)

    assert str(value) == "7.0.0"


def test_semantic_version_bump_helpers_apply_expected_transitions():
    value = SemanticVersion.from_raw("1.2.3")

    assert str(value.bump_patch()) == "1.2.4"
    assert str(value.bump_minor()) == "1.3.0"
    assert str(value.bump_major()) == "2.0.0"
    assert str(value.bumped(VersionBumpType.MINOR)) == "1.3.0"


def test_topic_slug_normalize_uses_lookup_aliases():
    lookup = {
        "sdks & tools": "sdk-tools",
        "sdks-tools": "sdk-tools",
        "sdk-tools": "sdk-tools",
    }

    normalized = TopicSlug.normalize("SDKs & Tools", lookup)

    assert normalized is not None
    assert normalized.value == "sdk-tools"


def test_topic_slug_from_raw_returns_none_for_blank_values():
    assert TopicSlug.from_raw(None) is None
    assert TopicSlug.from_raw("   ") is None
