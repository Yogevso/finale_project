from __future__ import annotations

import base64
import html
import zipfile
from pathlib import Path

from app.conversion.html_generator import ir_to_html
from app.conversion.pptx_extractor import HeadingItem, extract_pptx

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"
RICH_PPTX_FIXTURE = FIXTURE_DIR / "wave_y_rich.pptx"
EMPTY_PPTX_FIXTURE = FIXTURE_DIR / "wave_y_empty.pptx"

SLIDE_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)
IMAGE_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
)
NOTES_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
)
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRXcAAAAASUVORK5CYII="
)


def _write_pptx(
    path: Path,
    *,
    slides: list[dict[str, object]] | None = None,
    title: str | None = None,
    author: str | None = None,
    extra_files: dict[str, str | bytes] | None = None,
) -> None:
    slide_entries = slides or []
    slide_overrides = "".join(
        (
            '<Override PartName="/ppt/'
            f'{slide["target"]}" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.slide+xml"/>'
        )
        for slide in slide_entries
    )
    extra_overrides = "".join(
        _content_type_override(archive_path)
        for archive_path in (extra_files or {})
        if archive_path.endswith(".xml")
    )
    slide_id_list = "".join(
        f'<p:sldId id="{256 + index}" r:id="{slide["relationship_id"]}"/>'
        for index, slide in enumerate(slide_entries)
    )
    presentation_relationships = "".join(
        (
            f'<Relationship Id="{slide["relationship_id"]}" '
            f'Type="{SLIDE_RELATIONSHIP_TYPE}" '
            f'Target="{slide["target"]}"/>'
        )
        for slide in slide_entries
    )
    title_xml = f"<dc:title>{html.escape(title)}</dc:title>" if title else ""
    author_xml = f"<dc:creator>{html.escape(author)}</dc:creator>" if author else ""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Default Extension="png" ContentType="image/png"/>'
                '<Override PartName="/ppt/presentation.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'presentationml.presentation.main+xml"/>'
                '<Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                f"{slide_overrides}{extra_overrides}"
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<Relationships "
                'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" Target="ppt/presentation.xml"/>'
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/package/2006/relationships/'
                'metadata/core-properties" Target="docProps/core.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "docProps/core.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<cp:coreProperties "
                'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
                'core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" '
                'xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f"{title_xml}{author_xml}"
                '<dcterms:created xsi:type="dcterms:W3CDTF">2026-03-10T10:00:00Z'
                "</dcterms:created>"
                '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-03-10T11:00:00Z'
                "</dcterms:modified>"
                "</cp:coreProperties>"
            ),
        )
        archive.writestr(
            "ppt/presentation.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<p:presentation "
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                f"<p:sldIdLst>{slide_id_list}</p:sldIdLst>"
                "</p:presentation>"
            ),
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<Relationships "
                'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f"{presentation_relationships}"
                "</Relationships>"
            ),
        )

        for slide in slide_entries:
            target = str(slide["target"])
            archive.writestr(f"ppt/{target}", str(slide["xml"]))
            relationships = slide.get("relationships", [])
            if relationships:
                archive.writestr(
                    _slide_relationships_path(target),
                    _relationships_xml(relationships),
                )

        for archive_path, content in (extra_files or {}).items():
            archive.writestr(archive_path, content)


def _content_type_override(archive_path: str) -> str:
    if archive_path.startswith("ppt/notesSlides/"):
        return (
            '<Override PartName="/'
            f'{archive_path}" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.notesSlide+xml"/>'
        )
    return ""


def _slide_relationships_path(target: str) -> str:
    slide_name = Path(target).name
    return f"ppt/slides/_rels/{slide_name}.rels"


def _relationships_xml(relationships: list[tuple[str, str, str]]) -> str:
    items = "".join(
        (
            f'<Relationship Id="{relationship_id}" '
            f'Type="{relationship_type}" '
            f'Target="{target}"/>'
        )
        for relationship_id, relationship_type, target in relationships
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        "<Relationships "
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{items}"
        "</Relationships>"
    )


def _write_ratio_bomb_pptx(path: Path, *, repeat_count: int = 2_000_000) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/ppt/presentation.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'presentationml.presentation.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<Relationships "
                'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" Target="ppt/presentation.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "ppt/presentation.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                "<p:presentation "
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                "<p:sldIdLst></p:sldIdLst>"
                "</p:presentation>"
            ),
        )
        archive.writestr("ppt/bomb.txt", "A" * repeat_count)


def _make_slide(*nodes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<p:cSld><p:spTree>'
        f'{"".join(nodes)}'
        "</p:spTree></p:cSld>"
        "</p:sld>"
    )


def _make_notes(*paragraphs: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:notes '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        f'{_make_shape(501, list(paragraphs), placeholder_type="body", name="Notes")}'
        "</p:spTree></p:cSld>"
        "</p:notes>"
    )


def _make_shape(
    shape_id: int,
    paragraphs: list[str],
    *,
    placeholder_type: str | None = None,
    name: str | None = None,
) -> str:
    placeholder_xml = f'<p:ph type="{placeholder_type}"/>' if placeholder_type else ""
    return (
        "<p:sp>"
        "<p:nvSpPr>"
        f'<p:cNvPr id="{shape_id}" name="{html.escape(name or f"Shape {shape_id}")}"/>'
        "<p:cNvSpPr/>"
        f"<p:nvPr>{placeholder_xml}</p:nvPr>"
        "</p:nvSpPr>"
        "<p:spPr/>"
        "<p:txBody><a:bodyPr/><a:lstStyle/>"
        f'{"".join(paragraphs)}'
        "</p:txBody>"
        "</p:sp>"
    )


def _make_picture(
    picture_id: int,
    relationship_id: str,
    *,
    name: str = "Picture",
    description: str | None = None,
) -> str:
    description_attr = f' descr="{html.escape(description)}"' if description else ""
    return (
        "<p:pic>"
        "<p:nvPicPr>"
        f'<p:cNvPr id="{picture_id}" name="{html.escape(name)}"{description_attr}/>'
        "<p:cNvPicPr/>"
        "<p:nvPr/>"
        "</p:nvPicPr>"
        "<p:blipFill>"
        f'<a:blip r:embed="{relationship_id}"/>'
        "<a:stretch><a:fillRect/></a:stretch>"
        "</p:blipFill>"
        "<p:spPr/>"
        "</p:pic>"
    )


def _make_paragraph(
    *runs: str | dict[str, object],
    bullet: bool = False,
    ordered: bool = False,
    level: int = 0,
) -> str:
    p_pr = ""
    if bullet or ordered or level:
        bullet_xml = ""
        if ordered:
            bullet_xml = '<a:buAutoNum type="arabicPeriod" startAt="1"/>'
        elif bullet:
            bullet_xml = '<a:buChar char="•"/>'
        level_attr = f' lvl="{level}"' if level else ""
        p_pr = f"<a:pPr{level_attr}>{bullet_xml}</a:pPr>"
    return f"<a:p>{p_pr}{''.join(_make_run(run) for run in runs)}</a:p>"


def _make_run(run: str | dict[str, object]) -> str:
    if isinstance(run, str):
        return f"<a:r><a:t>{html.escape(run)}</a:t></a:r>"

    attributes: list[str] = []
    if run.get("bold"):
        attributes.append(' b="1"')
    if run.get("italic"):
        attributes.append(' i="1"')

    return f'<a:r><a:rPr{"".join(attributes)}/>' f'<a:t>{html.escape(str(run["text"]))}</a:t></a:r>'


def test_extract_pptx_returns_ready_result_for_valid_presentation(tmp_path):
    pptx_path = tmp_path / "slides.pptx"
    _write_pptx(
        pptx_path,
        slides=[
            {
                "relationship_id": "rId7",
                "target": "slides/slide2.xml",
                "xml": _make_slide(),
            },
            {
                "relationship_id": "rId3",
                "target": "slides/slide1.xml",
                "xml": _make_slide(),
            },
        ],
        title="Quarterly Review",
        author="Codex",
    )

    result = extract_pptx(pptx_path)

    assert result.status == "ready"
    assert result.title == "Quarterly Review"
    assert result.metadata["title"] == "Quarterly Review"
    assert result.metadata["author"] == "Codex"
    assert result.metadata["slideCount"] == 2
    assert result.html == (
        '<div class="pptx-presentation" data-slide-count="2">'
        '<section class="pptx-slide" id="slide-1" data-slide-number="1" '
        'aria-label="Slide 1"><span class="slide-badge" aria-label="Slide 1 of 2">'
        'Slide 1</span><h2 id="slide-1-title">Slide 1</h2></section>'
        '<section class="pptx-slide" id="slide-2" data-slide-number="2" '
        'aria-label="Slide 2"><span class="slide-badge" aria-label="Slide 2 of 2">'
        'Slide 2</span><h2 id="slide-2-title">Slide 2</h2></section>'
        "</div>"
    )
    assert [(slide.number, slide.archive_path) for slide in result.slides] == [
        (1, "ppt/slides/slide2.xml"),
        (2, "ppt/slides/slide1.xml"),
    ]
    assert result.headings == [
        HeadingItem(id="slide-1-title", level=2, text="Slide 1", slide_number=1),
        HeadingItem(id="slide-2-title", level=2, text="Slide 2", slide_number=2),
    ]
    assert result.ir is not None
    assert ir_to_html(result.ir) == result.html
    assert result.warnings == []
    assert result.confidence == 1.0
    assert result.extraction_error is None


def test_extract_pptx_renders_titles_text_boxes_bullets_images_and_notes(tmp_path):
    pptx_path = tmp_path / "rich-deck.pptx"
    rich_slide = _make_slide(
        _make_shape(10, [_make_paragraph("Welcome")], placeholder_type="title", name="Title"),
        _make_shape(
            20,
            [
                _make_paragraph("Overview paragraph"),
                _make_paragraph({"text": "Italic detail", "italic": True}),
            ],
            placeholder_type="body",
            name="Body",
        ),
        _make_shape(
            30,
            [
                _make_paragraph("First point", bullet=True),
                _make_paragraph({"text": "Second", "bold": True}, " point", bullet=True),
                _make_paragraph("Nested point", bullet=True, level=1),
                _make_paragraph("Step one", ordered=True),
                _make_paragraph("Step two", ordered=True),
            ],
            name="Bullets",
        ),
        _make_picture(40, "rIdImage1", name="Architecture", description="Architecture diagram"),
    )
    notes_xml = _make_notes(
        _make_paragraph("Remember rollout order"),
        _make_paragraph({"text": "Backup note", "italic": True}),
    )
    _write_pptx(
        pptx_path,
        slides=[
            {
                "relationship_id": "rId5",
                "target": "slides/slide1.xml",
                "xml": rich_slide,
                "relationships": [
                    ("rIdImage1", IMAGE_RELATIONSHIP_TYPE, "../media/architecture.png"),
                    ("rIdNotes1", NOTES_RELATIONSHIP_TYPE, "../notesSlides/notesSlide1.xml"),
                ],
            }
        ],
        extra_files={
            "ppt/media/architecture.png": TINY_PNG_BYTES,
            "ppt/notesSlides/notesSlide1.xml": notes_xml,
        },
    )

    result = extract_pptx(pptx_path)

    assert result.status == "ready"
    assert result.title == "Welcome"
    assert result.metadata["slideCount"] == 1
    assert result.headings == [
        HeadingItem(id="slide-1-title", level=2, text="Welcome", slide_number=1),
    ]
    assert result.slides[0].title == "Welcome"
    assert result.slides[0].has_images is True
    assert result.slides[0].has_notes is True
    assert result.html == (
        '<div class="pptx-presentation" data-slide-count="1">'
        '<section class="pptx-slide" id="slide-1" data-slide-number="1" '
        'aria-label="Slide 1: Welcome"><span class="slide-badge" '
        'aria-label="Slide 1 of 1">Slide 1</span><h2 id="slide-1-title">Welcome</h2>'
        '<p>Overview paragraph</p><p><em>Italic detail</em></p>'
        '<ul class="slide-bullets"><li>First point</li><li><strong>Second</strong> point'
        '<ul><li>Nested point</li></ul></li></ul>'
        '<ol class="slide-bullets"><li>Step one</li><li>Step two</li></ol>'
        '<div class="slide-images"><figure><img src="data:image/png;base64,'
        f'{base64.b64encode(TINY_PNG_BYTES).decode("ascii")}" '
        'alt="Architecture diagram" loading="lazy" /></figure></div>'
        '<details class="speaker-notes"><summary aria-expanded="false">'
        'Speaker Notes (click to expand)</summary><div class="notes-content">'
        '<p>Remember rollout order</p><p><em>Backup note</em></p>'
        "</div></details></section></div>"
    )
    assert result.warnings == []
    assert result.confidence == 1.0


def test_extract_pptx_uses_slide_number_when_title_placeholder_is_missing(tmp_path):
    pptx_path = tmp_path / "untitled.pptx"
    _write_pptx(
        pptx_path,
        slides=[
            {
                "relationship_id": "rId3",
                "target": "slides/slide1.xml",
                "xml": _make_slide(_make_shape(10, [_make_paragraph("Body only")], name="Body")),
            }
        ],
    )

    result = extract_pptx(pptx_path)

    assert result.status == "ready"
    assert result.title == "Slide 1"
    assert result.headings == [
        HeadingItem(id="slide-1-title", level=2, text="Slide 1", slide_number=1),
    ]
    assert (
        '<section class="pptx-slide" id="slide-1" data-slide-number="1" aria-label="Slide 1">'
        '<span class="slide-badge" aria-label="Slide 1 of 1">Slide 1</span>'
        '<h2 id="slide-1-title">Slide 1</h2><p>Body only</p></section>'
    ) in result.html


def test_extract_pptx_renders_missing_images_and_truncated_notes(tmp_path):
    pptx_path = tmp_path / "missing-image.pptx"
    long_notes = "A" * 1005
    _write_pptx(
        pptx_path,
        slides=[
            {
                "relationship_id": "rId9",
                "target": "slides/slide1.xml",
                "xml": _make_slide(
                    _make_shape(10, [_make_paragraph("Deep Dive")], placeholder_type="title"),
                    _make_picture(20, "rIdMissingImage", description="Missing diagram"),
                ),
                "relationships": [
                    ("rIdMissingImage", IMAGE_RELATIONSHIP_TYPE, "../media/missing.png"),
                    ("rIdNotes1", NOTES_RELATIONSHIP_TYPE, "../notesSlides/notesSlide1.xml"),
                ],
            }
        ],
        extra_files={
            "ppt/notesSlides/notesSlide1.xml": _make_notes(_make_paragraph(long_notes)),
        },
    )

    result = extract_pptx(pptx_path)

    assert result.status == "ready"
    assert result.warnings[0].code == "MISSING_IMAGES"
    assert result.warnings[0].count == 1
    assert result.confidence == 0.9
    assert "[Image unavailable: Missing diagram]" in result.html
    assert ("A" * 997) + "..." in result.html


def test_extract_pptx_marks_empty_presentations_with_no_content_warning(tmp_path):
    pptx_path = tmp_path / "empty.pptx"
    _write_pptx(pptx_path, slides=[], title="Empty Deck", author="Codex")

    result = extract_pptx(pptx_path)

    assert result.status == "ready"
    assert result.title == "Empty Deck"
    assert result.metadata["slideCount"] == 0
    assert result.html == '<div class="pptx-presentation" data-slide-count="0"></div>'
    assert result.slides == []
    assert [warning.code for warning in result.warnings] == ["NO_CONTENT"]
    assert result.confidence == 0.5


def test_extract_pptx_fails_when_presentation_xml_is_missing(tmp_path):
    pptx_path = tmp_path / "missing-presentation.pptx"
    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")

    result = extract_pptx(pptx_path)

    assert result.status == "failed"
    assert result.html == ""
    assert result.confidence == 0.0
    assert result.extraction_error is not None
    assert "ppt/presentation.xml" in result.extraction_error
    assert [warning.code for warning in result.warnings] == ["PARSE_FAILED"]


def test_extract_pptx_fails_for_invalid_archives(tmp_path):
    invalid_path = tmp_path / "broken.pptx"
    invalid_path.write_text("not a pptx", encoding="utf-8")

    result = extract_pptx(invalid_path)

    assert result.status == "failed"
    assert result.html == ""
    assert result.confidence == 0.0
    assert result.extraction_error is not None
    assert "Invalid PPTX archive" in result.extraction_error
    assert [warning.code for warning in result.warnings] == ["PARSE_FAILED"]


def test_extract_pptx_rejects_unsafe_zip_bombs(tmp_path):
    bomb_path = tmp_path / "bomb.pptx"
    _write_ratio_bomb_pptx(bomb_path)

    result = extract_pptx(bomb_path)

    assert result.status == "failed"
    assert result.html == ""
    assert result.confidence == 0.0
    assert result.extraction_error is not None
    assert "Unsafe PPTX archive" in result.extraction_error
    assert "compression ratio limit" in result.extraction_error
    assert [warning.code for warning in result.warnings] == ["PARSE_FAILED"]


def test_extract_pptx_renders_wave_y_rich_fixture_file():
    result = extract_pptx(RICH_PPTX_FIXTURE)

    assert result.status == "ready"
    assert result.metadata["title"] == "Wave Y Rich Deck"
    assert result.metadata["author"] == "Codex"
    assert result.metadata["slideCount"] == 3
    assert result.ir is not None
    assert ir_to_html(result.ir) == result.html
    assert result.headings == [
        HeadingItem(id="slide-1-title", level=2, text="Wave Y Launch", slide_number=1),
        HeadingItem(id="slide-2-title", level=2, text="Deployment Checklist", slide_number=2),
        HeadingItem(id="slide-3-title", level=2, text="Slide 3", slide_number=3),
    ]
    assert (
        '<div class="pptx-presentation" data-slide-count="3">'
        '<section class="pptx-slide" id="slide-1" data-slide-number="1" '
        'aria-label="Slide 1: Wave Y Launch">'
    ) in result.html
    assert "Quarterly readiness review" in result.html
    assert (
        '<ul class="slide-bullets"><li>DOCX uploads now extract cleanly</li>'
        "<li><strong>PowerPoint decks</strong> render as vertical slides"
        "<ul><li>Warnings surface only when needed</li></ul></li></ul>"
    ) in result.html
    assert 'alt="Architecture snapshot" loading="lazy"' in result.html
    assert '<details class="speaker-notes"><summary aria-expanded="false">' in result.html
    assert "Call out extraction confidence." in result.html
    assert (
        '<section class="pptx-slide" id="slide-2" data-slide-number="2" '
        'aria-label="Slide 2: Deployment Checklist">'
    ) in result.html
    assert (
        '<ol class="slide-bullets"><li>Upload the DOCX fixture</li>'
        "<li>Verify table rendering</li><li>Confirm image lightbox<ol>"
        "<li>Inspect mobile scroll behavior</li></ol></li></ol>"
    ) in result.html
    assert 'alt="Checklist illustration" loading="lazy"' in result.html
    assert (
        '<section class="pptx-slide" id="slide-3" data-slide-number="3" ' 'aria-label="Slide 3">'
    ) in result.html
    assert '<h2 id="slide-3-title">Slide 3</h2>' in result.html
    assert "<em>Fallback titles</em> are still usable." in result.html
    assert result.warnings == []
    assert result.confidence == 1.0


def test_extract_pptx_marks_wave_y_empty_fixture_with_no_content_warning():
    result = extract_pptx(EMPTY_PPTX_FIXTURE)

    assert result.status == "ready"
    assert result.title == "Wave Y Empty Deck"
    assert result.metadata["title"] == "Wave Y Empty Deck"
    assert result.metadata["slideCount"] == 0
    assert result.html == '<div class="pptx-presentation" data-slide-count="0"></div>'
    assert result.slides == []
    assert [warning.code for warning in result.warnings] == ["NO_CONTENT"]
    assert result.confidence == 0.5
