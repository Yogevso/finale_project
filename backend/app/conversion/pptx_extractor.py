"""Dedicated PPTX extraction helpers for the Wave Y pipeline."""

from __future__ import annotations

import base64
import html
import logging
import posixpath
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from app.conversion.html_generator import ir_to_html
from app.conversion.ir import IRNode

logger = logging.getLogger(__name__)

XML_NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
PPT_PRESENTATION_PATH = "ppt/presentation.xml"
PPT_PRESENTATION_RELS_PATH = "ppt/_rels/presentation.xml.rels"
SLIDE_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)
IMAGE_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
)
NOTES_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
)
IMAGE_CONTENT_TYPES = {
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}
IGNORED_NOTES_PLACEHOLDERS = {"dt", "ftr", "hdr", "sldImg", "sldNum"}
MAX_NOTES_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class ExtractionWarning:
    """Non-fatal extraction issue."""

    code: str
    message: str
    count: int | None = None


@dataclass(frozen=True, slots=True)
class HeadingItem:
    """Heading metadata for downstream TOC consumers."""

    id: str
    level: int
    text: str
    slide_number: int | None = None


@dataclass(frozen=True, slots=True)
class SlideSummary:
    """Ordered slide metadata returned to downstream callers."""

    number: int
    archive_path: str
    title: str | None = None
    has_notes: bool = False
    has_images: bool = False

    @property
    def section_id(self) -> str:
        return f"slide-{self.number}"

    @property
    def title_id(self) -> str:
        return f"{self.section_id}-title"


@dataclass(frozen=True, slots=True)
class TextRun:
    """Inline text run extracted from a PPTX paragraph."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass(slots=True)
class SlideParagraph:
    """Single slide paragraph with optional list metadata."""

    runs: list[TextRun] = field(default_factory=list)
    list_type: str | None = None
    level: int = 0

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass(frozen=True, slots=True)
class SlideImage:
    """Embedded slide image rendered into HTML."""

    alt: str
    src: str | None = None
    missing: bool = False


@dataclass(slots=True)
class SlideBlock:
    """Ordered body block for a slide."""

    kind: str
    paragraphs: list[SlideParagraph] = field(default_factory=list)
    image: SlideImage | None = None


@dataclass(slots=True)
class ParsedSlide:
    """Structured slide data used to render HTML and headings."""

    summary: SlideSummary
    title_runs: list[TextRun] = field(default_factory=list)
    body_blocks: list[SlideBlock] = field(default_factory=list)
    notes_paragraphs: list[SlideParagraph] = field(default_factory=list)


@dataclass(slots=True)
class PartRelationships:
    """Resolved relationship targets for a package part."""

    id_to_target: dict[str, str] = field(default_factory=dict)
    by_type: dict[str, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class SlideListItem:
    """Single list item with optional nested children."""

    paragraph: SlideParagraph
    children: list["SlideListBlock"] = field(default_factory=list)


@dataclass(slots=True)
class SlideListBlock:
    """Structured nested list representation for slide text boxes."""

    ordered: bool
    level: int
    items: list[SlideListItem] = field(default_factory=list)


@dataclass(slots=True)
class ExtractionResult:
    """Structured PPTX extraction output."""

    status: str
    html: str = ""
    title: str | None = None
    headings: list[HeadingItem] = field(default_factory=list)
    slides: list[SlideSummary] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[ExtractionWarning] = field(default_factory=list)
    confidence: float = 0.0
    extraction_error: str | None = None
    ir: IRNode | None = None


@dataclass(slots=True)
class ParsedPptxPresentation:
    """Intermediate parsed PPTX state used by later extraction tasks."""

    metadata: dict[str, Any] = field(default_factory=dict)
    slides: list[ParsedSlide] = field(default_factory=list)


class PptxExtractor:
    """PPTX parser that validates archives and extracts ordered slide content."""

    def extract_path(self, file_path: str | Path) -> ExtractionResult:
        source_path = Path(file_path)
        return self.extract_bytes(source_path.read_bytes(), source_name=source_path.name)

    def extract_bytes(self, content: bytes, *, source_name: str = "<memory>") -> ExtractionResult:
        logger.info("PPTX extraction started for %s", source_name)

        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                if PPT_PRESENTATION_PATH not in archive.namelist():
                    raise ValueError("PPTX is missing ppt/presentation.xml")
                parsed_presentation = self._parse_archive(archive)
        except zipfile.BadZipFile as exc:
            logger.exception("PPTX extraction failed for %s: invalid ZIP archive", source_name)
            return self._failed_result("Invalid PPTX archive", exc)
        except Exception as exc:
            logger.exception("PPTX extraction failed for %s", source_name)
            return self._failed_result("PPTX extraction failed", exc)

        paragraphs = self._extract_paragraphs(parsed_presentation.slides)
        headings = self._extract_headings(parsed_presentation.slides)
        table_blocks = self._extract_tables(parsed_presentation.slides)
        image_blocks = self._extract_images(parsed_presentation.slides)
        presentation_ir = self._build_ir(parsed_presentation.slides)
        html_content = ir_to_html(presentation_ir)
        result = ExtractionResult(
            status="ready",
            html=html_content,
            title=self._resolve_document_title(parsed_presentation.metadata, parsed_presentation.slides),
            headings=headings,
            slides=[slide.summary for slide in parsed_presentation.slides],
            metadata=parsed_presentation.metadata,
            warnings=[],
            confidence=1.0,
            extraction_error=None,
            ir=presentation_ir,
        )
        result.warnings = self._verify(result)
        result.confidence = calculate_confidence(result)

        logger.info(
            "PPTX extraction completed for %s (slides=%s, paragraphs=%s, tables=%s, images=%s, confidence=%.2f)",
            source_name,
            len(result.slides),
            len(paragraphs),
            len(table_blocks),
            len(image_blocks),
            result.confidence,
        )
        return result

    def _parse_archive(self, archive: zipfile.ZipFile) -> ParsedPptxPresentation:
        metadata = self._parse_metadata(archive)
        slides = self._load_slides(archive)
        metadata["slideCount"] = len(slides)
        return ParsedPptxPresentation(metadata=metadata, slides=slides)

    def _extract_paragraphs(self, slides: list[ParsedSlide]) -> list[SlideParagraph]:
        paragraphs: list[SlideParagraph] = []
        for slide in slides:
            for block in slide.body_blocks:
                if block.kind == "text":
                    paragraphs.extend(block.paragraphs)
            paragraphs.extend(slide.notes_paragraphs)
        return paragraphs

    def _extract_headings(self, slides: list[ParsedSlide]) -> list[HeadingItem]:
        return self._build_heading_items(slides)

    def _extract_lists(self, paragraphs: list[SlideParagraph]) -> list[SlideListBlock]:
        return self._build_list_blocks(paragraphs)

    def _extract_tables(self, slides: list[ParsedSlide]) -> list[IRNode]:
        # Table shapes are not yet parsed into structured slide blocks in the Wave Y pipeline.
        return []

    def _extract_images(self, slides: list[ParsedSlide]) -> list[SlideImage]:
        images: list[SlideImage] = []
        for slide in slides:
            for block in slide.body_blocks:
                if block.kind == "image" and block.image is not None:
                    images.append(block.image)
        return images

    def _parse_metadata(self, archive: zipfile.ZipFile) -> dict[str, Any]:
        root = self._read_xml(archive, "docProps/core.xml", required=False)
        if root is None:
            return {}

        metadata: dict[str, Any] = {}
        title = self._find_text(root, "dc:title")
        author = self._find_text(root, "dc:creator")
        created = self._find_text(root, "dcterms:created")
        modified = self._find_text(root, "dcterms:modified")

        if title:
            metadata["title"] = title
        if author:
            metadata["author"] = author
        if created:
            metadata["created"] = created
        if modified:
            metadata["modified"] = modified
        return metadata

    def _load_slides(self, archive: zipfile.ZipFile) -> list[ParsedSlide]:
        presentation_root = self._read_xml(archive, PPT_PRESENTATION_PATH, required=True)
        presentation_relationships = self._load_part_relationships(
            archive,
            PPT_PRESENTATION_PATH,
        )

        slides: list[ParsedSlide] = []
        slide_id_attr = self._ns_attr("r", "id")
        slide_list = presentation_root.find("p:sldIdLst", XML_NAMESPACES)
        if slide_list is None:
            return slides

        slide_number = 0
        for slide_id in slide_list.findall("p:sldId", XML_NAMESPACES):
            show_value = (slide_id.get("show") or "").strip().lower()
            if show_value in {"0", "false", "off"}:
                continue

            relationship_id = slide_id.get(slide_id_attr)
            if not relationship_id:
                continue

            archive_path = presentation_relationships.id_to_target.get(relationship_id)
            if not archive_path or archive_path not in archive.namelist():
                continue

            slide_number += 1
            slides.append(
                self._parse_slide(
                    archive,
                    archive_path=archive_path,
                    slide_number=slide_number,
                )
            )
        return slides

    def _parse_slide(
        self,
        archive: zipfile.ZipFile,
        *,
        archive_path: str,
        slide_number: int,
    ) -> ParsedSlide:
        slide_root = self._read_xml(archive, archive_path, required=True)
        relationships = self._load_part_relationships(archive, archive_path)
        sp_tree = slide_root.find("p:cSld/p:spTree", XML_NAMESPACES)

        title_runs: list[TextRun] = []
        body_blocks: list[SlideBlock] = []
        image_number = 0

        if sp_tree is not None:
            for node in self._iter_content_nodes(sp_tree):
                local_name = self._local_name(node.tag)
                if local_name == "sp":
                    paragraphs = self._parse_shape_paragraphs(node)
                    if not paragraphs:
                        continue

                    placeholder_type = self._shape_placeholder_type(node)
                    if placeholder_type in {"ctrTitle", "title"} and not self._has_visible_text_runs(
                        title_runs,
                    ):
                        title_runs = self._flatten_paragraphs(paragraphs)
                        continue

                    body_blocks.append(SlideBlock(kind="text", paragraphs=paragraphs))
                    continue

                image_number += 1
                image = self._parse_image_block(
                    node,
                    archive=archive,
                    relationships=relationships,
                    slide_number=slide_number,
                    image_number=image_number,
                )
                if image is None:
                    image_number -= 1
                    continue
                body_blocks.append(SlideBlock(kind="image", image=image))

        notes_paragraphs = self._parse_notes_paragraphs(archive, relationships)
        detected_title = self._plain_text_from_runs(title_runs).strip() or None
        summary = SlideSummary(
            number=slide_number,
            archive_path=archive_path,
            title=detected_title,
            has_notes=bool(notes_paragraphs),
            has_images=any(block.image is not None for block in body_blocks),
        )
        return ParsedSlide(
            summary=summary,
            title_runs=title_runs,
            body_blocks=body_blocks,
            notes_paragraphs=notes_paragraphs,
        )

    def _parse_shape_paragraphs(self, shape_element: ET.Element) -> list[SlideParagraph]:
        text_body = shape_element.find("p:txBody", XML_NAMESPACES)
        if text_body is None:
            return []

        paragraphs: list[SlideParagraph] = []
        for paragraph_element in text_body.findall("a:p", XML_NAMESPACES):
            paragraph = self._parse_paragraph(paragraph_element)
            if paragraph.text.strip():
                paragraphs.append(paragraph)
        return paragraphs

    def _parse_paragraph(self, paragraph_element: ET.Element) -> SlideParagraph:
        paragraph_properties = paragraph_element.find("a:pPr", XML_NAMESPACES)
        list_type: str | None = None
        level = 0
        if paragraph_properties is not None:
            level = int(paragraph_properties.get("lvl", "0") or "0")
            if paragraph_properties.find("a:buAutoNum", XML_NAMESPACES) is not None:
                list_type = "ordered"
            elif paragraph_properties.find("a:buChar", XML_NAMESPACES) is not None:
                list_type = "unordered"

        runs: list[TextRun] = []
        for child in paragraph_element:
            local_name = self._local_name(child.tag)
            if local_name == "br":
                runs.append(TextRun(text="\n"))
                continue
            if local_name not in {"fld", "r"}:
                continue

            text_element = child.find("a:t", XML_NAMESPACES)
            if text_element is None or text_element.text is None:
                continue

            run_properties = child.find("a:rPr", XML_NAMESPACES)
            runs.append(
                TextRun(
                    text=text_element.text,
                    bold=self._run_flag_is_enabled(run_properties, "b"),
                    italic=self._run_flag_is_enabled(run_properties, "i"),
                )
            )

        return SlideParagraph(runs=runs, list_type=list_type, level=level)

    def _parse_image_block(
        self,
        node: ET.Element,
        *,
        archive: zipfile.ZipFile,
        relationships: PartRelationships,
        slide_number: int,
        image_number: int,
    ) -> SlideImage | None:
        blip = node.find(".//a:blip", XML_NAMESPACES)
        if blip is None:
            return None

        alt = self._image_alt_text(node, slide_number=slide_number, image_number=image_number)
        relationship_id = blip.get(self._ns_attr("r", "embed"))
        if not relationship_id:
            return SlideImage(alt=alt, missing=True)

        archive_path = relationships.id_to_target.get(relationship_id)
        if not archive_path or archive_path not in archive.namelist():
            return SlideImage(alt=alt, missing=True)

        image_bytes = archive.read(archive_path)
        content_type = self._image_content_type(archive_path)
        data_url = (
            f"data:{content_type};base64,"
            f"{base64.b64encode(image_bytes).decode('ascii')}"
        )
        return SlideImage(alt=alt, src=data_url, missing=False)

    def _parse_notes_paragraphs(
        self,
        archive: zipfile.ZipFile,
        relationships: PartRelationships,
    ) -> list[SlideParagraph]:
        notes_targets = relationships.by_type.get(NOTES_RELATIONSHIP_TYPE, [])
        if not notes_targets:
            return []

        notes_root = self._read_xml(archive, notes_targets[0], required=False)
        if notes_root is None:
            return []

        sp_tree = notes_root.find("p:cSld/p:spTree", XML_NAMESPACES)
        if sp_tree is None:
            return []

        paragraphs: list[SlideParagraph] = []
        for node in self._iter_content_nodes(sp_tree):
            if self._local_name(node.tag) != "sp":
                continue

            placeholder_type = self._shape_placeholder_type(node)
            if placeholder_type in IGNORED_NOTES_PLACEHOLDERS:
                continue

            paragraphs.extend(self._parse_shape_paragraphs(node))

        return self._truncate_notes(paragraphs)

    def _truncate_notes(self, paragraphs: list[SlideParagraph]) -> list[SlideParagraph]:
        note_text = "\n\n".join(paragraph.text.strip() for paragraph in paragraphs if paragraph.text.strip())
        if len(note_text) <= MAX_NOTES_LENGTH:
            return paragraphs

        truncated = note_text[: MAX_NOTES_LENGTH - 3].rstrip()
        return [SlideParagraph(runs=[TextRun(text=f"{truncated}...")])]

    def _load_part_relationships(
        self,
        archive: zipfile.ZipFile,
        source_part: str,
    ) -> PartRelationships:
        rels_root = self._read_xml(
            archive,
            self._relationships_path(source_part),
            required=False,
        )
        relationships = PartRelationships()
        if rels_root is None:
            return relationships

        for relationship in rels_root.findall("rel:Relationship", XML_NAMESPACES):
            relationship_id = relationship.get("Id")
            relationship_type = relationship.get("Type")
            target = relationship.get("Target")
            if not relationship_id or not relationship_type or not target:
                continue

            archive_path = self._resolve_archive_target(source_part, target)
            relationships.id_to_target[relationship_id] = archive_path
            relationships.by_type.setdefault(relationship_type, []).append(archive_path)
        return relationships

    def _build_heading_items(self, slides: list[ParsedSlide]) -> list[HeadingItem]:
        return [
            HeadingItem(
                id=slide.summary.title_id,
                level=2,
                text=self._display_title(slide),
                slide_number=slide.summary.number,
            )
            for slide in slides
        ]

    def _resolve_document_title(
        self,
        metadata: dict[str, Any],
        slides: list[ParsedSlide],
    ) -> str | None:
        if slides and slides[0].summary.title:
            return slides[0].summary.title

        metadata_title = str(metadata.get("title") or "") or None
        if metadata_title is not None:
            return metadata_title

        if slides:
            return self._display_title(slides[0])
        return None

    def _build_ir(self, slides: list[ParsedSlide]) -> IRNode:
        total_slides = len(slides)
        return IRNode(
            type="document",
            styles={"classes": ["pptx-presentation"]},
            attributes={"tag": "div", "data-slide-count": total_slides},
            children=[
                self._build_slide_ir(slide, total_slides=total_slides)
                for slide in slides
            ],
        )

    def _build_slide_ir(self, slide: ParsedSlide, *, total_slides: int) -> IRNode:
        display_title = self._display_title(slide)
        title_content = (
            self._format_inline_runs(slide.title_runs)
            if slide.title_runs
            else html.escape(display_title, quote=True)
        )
        aria_label = (
            f"Slide {slide.summary.number}: {display_title}"
            if slide.summary.title
            else f"Slide {slide.summary.number}"
        )
        children: list[IRNode] = [
            IRNode(
                type="heading",
                content=title_content,
                attributes={"level": 2, "id": slide.summary.title_id},
            )
        ]
        children.extend(self._build_slide_blocks_ir(slide.body_blocks))

        notes_node = self._build_notes_ir(slide.notes_paragraphs)
        if notes_node is not None:
            children.append(notes_node)

        return IRNode(
            type="slide",
            styles={
                "classes": ["pptx-slide"],
                "badge_classes": ["slide-badge"],
            },
            attributes={
                "id": slide.summary.section_id,
                "data-slide-number": slide.summary.number,
                "aria-label": aria_label,
                "badge_text": f"Slide {slide.summary.number}",
                "badge_label": f"Slide {slide.summary.number} of {total_slides}",
            },
            children=children,
        )

    def _build_slide_blocks_ir(self, blocks: list[SlideBlock]) -> list[IRNode]:
        children: list[IRNode] = []
        index = 0
        while index < len(blocks):
            block = blocks[index]
            if block.kind == "text":
                children.extend(self._build_text_box_ir(block.paragraphs))
                index += 1
                continue

            images, index = self._collect_image_run(blocks, index)
            image_group = self._build_image_group_ir(images)
            if image_group is not None:
                children.append(image_group)
        return children

    def _build_text_box_ir(self, paragraphs: list[SlideParagraph]) -> list[IRNode]:
        children: list[IRNode] = []
        index = 0
        while index < len(paragraphs):
            paragraph = paragraphs[index]
            if paragraph.list_type is None:
                paragraph_node = self._build_paragraph_ir(paragraph)
                if paragraph_node is not None:
                    children.append(paragraph_node)
                index += 1
                continue

            list_run, index = self._collect_list_run(paragraphs, index)
            children.extend(
                self._build_list_block_ir(block, root=True)
                for block in self._extract_lists(list_run)
            )
        return children

    def _build_notes_ir(self, paragraphs: list[SlideParagraph]) -> IRNode | None:
        if not paragraphs:
            return None

        return IRNode(
            type="notes",
            styles={
                "classes": ["speaker-notes"],
                "content_classes": ["notes-content"],
            },
            attributes={
                "summary": "Speaker Notes (click to expand)",
                "summary_attributes": {"aria-expanded": "false"},
            },
            children=self._build_text_box_ir(paragraphs),
        )

    def _build_paragraph_ir(self, paragraph: SlideParagraph) -> IRNode | None:
        text = paragraph.text.strip()
        if not text:
            return None
        return IRNode(type="paragraph", content=self._format_inline_runs(paragraph.runs))

    def _build_image_group_ir(self, images: list[SlideImage]) -> IRNode | None:
        if not images:
            return None
        return IRNode(
            type="container",
            styles={"classes": ["slide-images"]},
            attributes={"tag": "div"},
            children=[self._build_image_ir(image) for image in images],
        )

    def _build_image_ir(self, image: SlideImage) -> IRNode:
        return IRNode(
            type="image",
            attributes={
                "src": image.src,
                "alt": image.alt,
                "missing": image.missing,
                "loading": "lazy",
            },
        )

    def _build_list_block_ir(self, block: SlideListBlock, *, root: bool = False) -> IRNode:
        styles = {"classes": ["slide-bullets"]} if root else {}
        return IRNode(
            type="list",
            styles=styles,
            attributes={"ordered": block.ordered},
            children=[self._build_list_item_ir(item) for item in block.items],
        )

    def _build_list_item_ir(self, item: SlideListItem) -> IRNode:
        return IRNode(
            type="list-item",
            content=self._format_inline_runs(item.paragraph.runs),
            children=[self._build_list_block_ir(child) for child in item.children],
        )

    def _format_inline_runs(self, runs: list[TextRun]) -> str:
        return "".join(self._format_run(run) for run in runs)

    def _format_run(self, run: TextRun) -> str:
        rendered = html.escape(run.text, quote=True).replace("\n", "<br/>")
        if run.italic:
            rendered = f"<em>{rendered}</em>"
        if run.bold:
            rendered = f"<strong>{rendered}</strong>"
        return rendered

    def _collect_image_run(
        self,
        blocks: list[SlideBlock],
        start_index: int,
    ) -> tuple[list[SlideImage], int]:
        images: list[SlideImage] = []
        index = start_index
        while index < len(blocks):
            block = blocks[index]
            if block.kind != "image" or block.image is None:
                break
            images.append(block.image)
            index += 1
        return images, index

    def _collect_list_run(
        self,
        paragraphs: list[SlideParagraph],
        start_index: int,
    ) -> tuple[list[SlideParagraph], int]:
        run: list[SlideParagraph] = []
        index = start_index
        while index < len(paragraphs):
            paragraph = paragraphs[index]
            if paragraph.list_type is None:
                break
            run.append(paragraph)
            index += 1
        return run, index

    def _build_list_blocks(self, paragraphs: list[SlideParagraph]) -> list[SlideListBlock]:
        blocks: list[SlideListBlock] = []
        index = 0
        while index < len(paragraphs):
            block, index = self._parse_list_block(
                paragraphs,
                start_index=index,
                level=paragraphs[index].level,
            )
            blocks.append(block)
        return blocks

    def _parse_list_block(
        self,
        paragraphs: list[SlideParagraph],
        *,
        start_index: int,
        level: int,
    ) -> tuple[SlideListBlock, int]:
        start_paragraph = paragraphs[start_index]
        block = SlideListBlock(
            ordered=start_paragraph.list_type == "ordered",
            level=level,
        )
        index = start_index

        while index < len(paragraphs):
            paragraph = paragraphs[index]
            if paragraph.level < level:
                break

            if paragraph.level > level:
                if not block.items:
                    break
                child_block, index = self._parse_list_block(
                    paragraphs,
                    start_index=index,
                    level=paragraph.level,
                )
                block.items[-1].children.append(child_block)
                continue

            if block.items and (paragraph.list_type == "ordered") != block.ordered:
                break

            block.items.append(SlideListItem(paragraph=paragraph))
            index += 1

        return block, index

    def _verify(self, result: ExtractionResult) -> list[ExtractionWarning]:
        warnings: list[ExtractionWarning] = []
        if not result.slides:
            warnings.append(ExtractionWarning(code="NO_CONTENT", message="Presentation has no slides"))

        missing_image_count = result.html.count("[Image")
        if missing_image_count > 0:
            warnings.append(
                ExtractionWarning(
                    code="MISSING_IMAGES",
                    message=f"{missing_image_count} images failed",
                    count=missing_image_count,
                )
            )
        return warnings

    def _read_xml(
        self,
        archive: zipfile.ZipFile,
        archive_path: str,
        *,
        required: bool,
    ) -> ET.Element | None:
        try:
            xml_bytes = archive.read(archive_path)
        except KeyError:
            if required:
                raise ValueError(f"PPTX archive is missing {archive_path}") from None
            return None

        try:
            return ET.fromstring(xml_bytes)
        except ET.ParseError:
            if required:
                raise ValueError(f"PPTX XML at {archive_path} could not be parsed") from None
            logger.warning("Skipping unreadable optional PPTX XML: %s", archive_path)
            return None

    def _find_text(self, root: ET.Element, path: str) -> str | None:
        element = root.find(path, XML_NAMESPACES)
        if element is None or element.text is None:
            return None
        text = element.text.strip()
        return text or None

    def _run_flag_is_enabled(self, run_properties: ET.Element | None, attribute_name: str) -> bool:
        if run_properties is None:
            return False
        value = (run_properties.get(attribute_name) or "").strip().lower()
        return value in {"1", "true", "on"}

    def _flatten_paragraphs(self, paragraphs: list[SlideParagraph]) -> list[TextRun]:
        runs: list[TextRun] = []
        for index, paragraph in enumerate(paragraphs):
            if index > 0:
                runs.append(TextRun(text="\n"))
            runs.extend(paragraph.runs)
        return runs

    def _has_visible_text_runs(self, runs: list[TextRun]) -> bool:
        return bool(self._plain_text_from_runs(runs).strip())

    def _plain_text_from_runs(self, runs: list[TextRun]) -> str:
        return "".join(run.text for run in runs)

    def _display_title(self, slide: ParsedSlide) -> str:
        return slide.summary.title or f"Slide {slide.summary.number}"

    def _shape_placeholder_type(self, shape_element: ET.Element) -> str | None:
        placeholder = shape_element.find("p:nvSpPr/p:nvPr/p:ph", XML_NAMESPACES)
        if placeholder is None:
            return None
        return (placeholder.get("type") or "body").strip() or "body"

    def _image_alt_text(self, node: ET.Element, *, slide_number: int, image_number: int) -> str:
        for candidate in node.iter():
            if self._local_name(candidate.tag) != "cNvPr":
                continue
            description = (candidate.get("descr") or "").strip()
            if description:
                return description
            name = (candidate.get("name") or "").strip()
            if name:
                return name
        return f"Slide {slide_number} image {image_number}"

    def _relationships_path(self, source_part: str) -> str:
        source_dir = posixpath.dirname(source_part)
        source_name = posixpath.basename(source_part)
        return posixpath.join(source_dir, "_rels", f"{source_name}.rels")

    def _iter_content_nodes(self, container: ET.Element):
        for child in container:
            local_name = self._local_name(child.tag)
            if local_name == "grpSp":
                yield from self._iter_content_nodes(child)
                continue
            if local_name in {"graphicFrame", "pic", "sp"}:
                yield child

    def _image_content_type(self, archive_path: str) -> str:
        extension = Path(archive_path).suffix.lower()
        return IMAGE_CONTENT_TYPES.get(extension, "application/octet-stream")

    def _resolve_archive_target(self, source_part: str, target: str) -> str:
        source_dir = posixpath.dirname(source_part)
        resolved = posixpath.normpath(posixpath.join(source_dir, target))
        return resolved.lstrip("/")

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", maxsplit=1)[-1]

    def _ns_attr(self, prefix: str, attribute: str) -> str:
        return f"{{{XML_NAMESPACES[prefix]}}}{attribute}"

    def _failed_result(self, message: str, exc: Exception) -> ExtractionResult:
        warning = ExtractionWarning(code="PARSE_FAILED", message=f"{message}: {exc}")
        return ExtractionResult(
            status="failed",
            html="",
            title=None,
            headings=[],
            slides=[],
            metadata={},
            warnings=[warning],
            confidence=0.0,
            extraction_error=f"{message}: {exc}",
        )


def calculate_confidence(result: ExtractionResult) -> float:
    """Best-effort confidence score based on current warning set."""

    score = 1.0
    for warning in result.warnings:
        if warning.code == "PARSE_FAILED":
            score -= 1.0
        elif warning.code == "MISSING_IMAGES":
            score -= 0.1 * float(warning.count or 1)
        elif warning.code == "NO_CONTENT":
            score -= 0.5
    return max(0.0, min(1.0, score))


def extract_pptx(file_path: str | Path) -> ExtractionResult:
    """Parse a PPTX file path into a structured extraction result."""

    return PptxExtractor().extract_path(file_path)


__all__ = [
    "ExtractionResult",
    "ExtractionWarning",
    "HeadingItem",
    "PptxExtractor",
    "SlideSummary",
    "calculate_confidence",
    "extract_pptx",
]
