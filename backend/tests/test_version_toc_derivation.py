"""Tests for rebuilding a version's contents after an edit.

An edit produces HTML, never the original file, so the contents cannot be read
from a DOCX contents page again. Leaving them empty made a review report all 158
entries as removed when a single section had been touched.
"""

from __future__ import annotations

from app.conversion.version_toc import derive_version_toc

BASELINE = [
    {
        "id": "toc-0",
        "title": "1 Release Kit Summary",
        "level": 1,
        "page": 10,
        "page_start": 10,
        "page_end": None,
        "anchor_id": "heading-release-kit-summary",
    },
    {
        "id": "toc-1",
        "title": "1.1 Release Kit Details",
        "level": 2,
        "page": 10,
        "page_start": 10,
        "page_end": None,
        "anchor_id": "heading-release-kit-details",
    },
]

HTML = (
    '<h1 id="heading-release-kit-summary">Release Kit Summary</h1><p>body</p>'
    '<h2 id="heading-release-kit-details">Release Kit Details</h2><p>body</p>'
)


def test_pages_are_carried_across_from_the_previous_version():
    """HTML never holds page numbers; the previous entries do."""
    derived = derive_version_toc(HTML, BASELINE)

    assert [entry["page"] for entry in derived] == [10, 10]
    assert [entry["page_start"] for entry in derived] == [10, 10]


def test_an_untouched_document_derives_entries_identical_to_the_baseline():
    derived = derive_version_toc(HTML, BASELINE)

    assert [(e["title"], e["page"], e["anchor_id"]) for e in derived] == [
        (e["title"], e["page"], e["anchor_id"]) for e in BASELINE
    ], "an unchanged document must not look edited to a review"


def test_a_renamed_heading_keeps_its_number_and_its_page():
    """Renaming section 1 does not stop it being section 1."""
    edited = HTML.replace(">Release Kit Summary<", ">Release Kit Summary+YAKIR%<")

    derived = derive_version_toc(edited, BASELINE)

    assert derived[0]["title"] == "1 Release Kit Summary+YAKIR%"
    assert derived[0]["page"] == 10
    assert derived[1]["title"] == "1.1 Release Kit Details"


def test_a_heading_that_already_shows_its_number_is_not_numbered_twice():
    html = '<h1 id="heading-x">2 General Information</h1>'
    baseline = [{"title": "2 General Information", "page": 11, "anchor_id": "heading-x"}]

    assert derive_version_toc(html, baseline)[0]["title"] == "2 General Information"


def test_a_new_heading_appears_without_inventing_a_page_from_thin_air():
    html = HTML + '<h2 id="heading-new">Newly Added</h2>'

    derived = derive_version_toc(html, BASELINE)

    assert len(derived) == 3
    assert derived[2]["title"] == "Newly Added"
    assert derived[2]["page"] == 3, "an unknown page falls back to position, not to null"


def test_a_deleted_heading_disappears_from_the_contents():
    html = '<h1 id="heading-release-kit-summary">Release Kit Summary</h1>'

    derived = derive_version_toc(html, BASELINE)

    assert [entry["anchor_id"] for entry in derived] == ["heading-release-kit-summary"]


def test_content_without_headings_yields_no_contents():
    assert derive_version_toc("<p>just prose</p>", BASELINE) == []
    assert derive_version_toc("", BASELINE) == []
    assert derive_version_toc(None, BASELINE) == []


def test_a_missing_or_broken_baseline_is_tolerated():
    derived = derive_version_toc(HTML, None)

    assert len(derived) == 2
    assert [entry["page"] for entry in derived] == [1, 2]
