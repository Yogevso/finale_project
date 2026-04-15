"""IR to semantic HTML rendering for extracted office documents."""

from __future__ import annotations

import html
from typing import Any

from app.conversion.ir import IRNode


def ir_to_html(node: IRNode | None) -> str:
    """Render an IR tree into semantic HTML."""
    if node is None:
        return ""

    match node.type:
        case "document":
            return _render_document(node)
        case "container":
            return _render_container(node)
        case "heading":
            return _render_heading(node)
        case "paragraph":
            return _render_paragraph(node)
        case "list":
            return _render_list(node)
        case "list-item":
            return _render_list_item(node)
        case "table":
            return _render_table(node)
        case "table-row":
            return _render_table_row(node)
        case "table-cell":
            return _render_table_cell(node)
        case "image":
            return _render_image(node)
        case "slide":
            return _render_slide(node)
        case "notes":
            return _render_notes(node)
        case _:
            return _render_container(node)


def _render_document(node: IRNode) -> str:
    tag = str(node.attributes.get("tag") or "").strip()
    inner = f"{node.content}{_render_children(node.children)}"
    if not tag:
        return inner
    attrs = _render_attrs(node.attributes, node.styles, reserved={"tag"})
    return f"<{tag}{attrs}>{inner}</{tag}>"


def _render_container(node: IRNode) -> str:
    tag = str(node.attributes.get("tag") or "div").strip() or "div"
    attrs = _render_attrs(node.attributes, node.styles, reserved={"tag"})
    return f"<{tag}{attrs}>{node.content}{_render_children(node.children)}</{tag}>"


def _render_heading(node: IRNode) -> str:
    level = max(1, min(6, int(node.attributes.get("level", 1) or 1)))
    attrs = _render_attrs(node.attributes, node.styles, reserved={"level"})
    return f"<h{level}{attrs}>{node.content}</h{level}>"


def _render_paragraph(node: IRNode) -> str:
    attrs = _render_attrs(node.attributes, node.styles)
    return f"<p{attrs}>{node.content}</p>"


def _render_list(node: IRNode) -> str:
    tag = "ol" if node.attributes.get("ordered") else "ul"
    attrs = _render_attrs(node.attributes, node.styles, reserved={"ordered"})
    return f"<{tag}{attrs}>{_render_children(node.children)}</{tag}>"


def _render_list_item(node: IRNode) -> str:
    attrs = _render_attrs(node.attributes, node.styles)
    return f"<li{attrs}>{node.content}{_render_children(node.children)}</li>"


def _render_table(node: IRNode) -> str:
    wrapper_classes = _style_classes(node.styles, "wrapper_classes") or ["table-wrapper"]
    table_classes = _style_classes(node.styles, "table_classes")

    header_rows = [
        ir_to_html(child)
        for child in node.children
        if str(child.attributes.get("section") or "").lower() == "thead"
    ]
    body_rows = [
        ir_to_html(child)
        for child in node.children
        if str(child.attributes.get("section") or "").lower() != "thead"
    ]

    table_attrs = _render_attrs(node.attributes, {"classes": table_classes}, reserved={"section"})
    wrapper_attr = _render_class_attr(wrapper_classes)
    return (
        f"<div{wrapper_attr}>"
        f"<table{table_attrs}><thead>{''.join(header_rows)}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
        "</div>"
    )


def _render_table_row(node: IRNode) -> str:
    attrs = _render_attrs(node.attributes, node.styles, reserved={"section"})
    return f"<tr{attrs}>{_render_children(node.children)}</tr>"


def _render_table_cell(node: IRNode) -> str:
    tag = "th" if node.attributes.get("header") else "td"
    attrs = _render_attrs(node.attributes, node.styles, reserved={"header"})
    return f"<{tag}{attrs}>{node.content}{_render_children(node.children)}</{tag}>"


def _render_image(node: IRNode) -> str:
    alt = str(node.attributes.get("alt") or "")
    src = node.attributes.get("src")
    caption = str(node.attributes.get("caption") or "")
    loading = str(node.attributes.get("loading") or "lazy")
    placeholder_classes = _style_classes(node.styles, "placeholder_classes") or [
        "extracted-image-placeholder"
    ]
    caption_classes = _style_classes(node.styles, "caption_classes")
    figure_attrs = _render_attrs(
        node.attributes,
        node.styles,
        reserved={"alt", "src", "caption", "loading", "missing"},
    )
    caption_html = ""
    if caption:
        caption_attr = _render_class_attr(caption_classes)
        caption_html = f"<figcaption{caption_attr}>{html.escape(caption, quote=True)}</figcaption>"

    if node.attributes.get("missing") or not src:
        placeholder_attr = _render_class_attr(placeholder_classes)
        placeholder_text = html.escape(f"[Image unavailable: {alt}]", quote=True)
        return (
            f"<figure{figure_attrs}>"
            f"<div{placeholder_attr}>{placeholder_text}</div>"
            f"{caption_html}</figure>"
        )

    image_attrs = (
        f' src="{html.escape(str(src), quote=True)}"'
        f' alt="{html.escape(alt, quote=True)}"'
        f' loading="{html.escape(loading, quote=True)}"'
    )
    width = node.attributes.get("width")
    height = node.attributes.get("height")
    if width is not None:
        image_attrs += f' width="{int(width)}"'
    if height is not None:
        image_attrs += f' height="{int(height)}"'
    return f"<figure{figure_attrs}><img{image_attrs} />{caption_html}</figure>"


def _render_slide(node: IRNode) -> str:
    badge_text = str(node.attributes.get("badge_text") or "")
    badge_label = str(node.attributes.get("badge_label") or "")
    badge_classes = _style_classes(node.styles, "badge_classes") or ["slide-badge"]
    attrs = _render_attrs(node.attributes, node.styles, reserved={"badge_text", "badge_label"})
    badge_attr = _render_class_attr(badge_classes)
    if badge_label:
        badge_attr = _append_attr(
            badge_attr,
            f' aria-label="{html.escape(badge_label, quote=True)}"',
        )
    return (
        f"<section{attrs}>"
        f"<span{badge_attr}>{html.escape(badge_text, quote=True)}</span>"
        f"{_render_children(node.children)}"
        "</section>"
    )


def _render_notes(node: IRNode) -> str:
    summary = str(node.attributes.get("summary") or "Speaker Notes")
    summary_attrs = dict(node.attributes.get("summary_attributes") or {})
    content_attributes = dict(node.attributes.get("content_attributes") or {})
    details_attrs = _render_attrs(
        node.attributes,
        node.styles,
        reserved={"summary", "summary_attributes", "content_attributes"},
    )
    summary_attr = _render_attrs(summary_attrs)
    content_attr = _render_attrs(
        content_attributes,
        {"classes": _style_classes(node.styles, "content_classes")},
    )
    return (
        f"<details{details_attrs}>"
        f"<summary{summary_attr}>{html.escape(summary, quote=True)}</summary>"
        f"<div{content_attr}>{_render_children(node.children)}</div>"
        "</details>"
    )


def _render_children(children: list[IRNode]) -> str:
    return "".join(ir_to_html(child) for child in children)


def _render_attrs(
    attributes: dict[str, Any] | None,
    styles: dict[str, Any] | None = None,
    *,
    reserved: set[str] | None = None,
) -> str:
    reserved = reserved or set()
    attributes = attributes or {}
    styles = styles or {}

    rendered: list[str] = []
    class_attr = _render_class_attr(_style_classes(styles, "classes"))
    if class_attr:
        rendered.append(class_attr)

    for key, value in attributes.items():
        if key in reserved or value is None:
            continue
        if isinstance(value, bool):
            if value:
                rendered.append(f" {key}")
            continue
        if isinstance(value, (dict, list, tuple)):
            continue
        rendered.append(f' {key}="{html.escape(str(value), quote=True)}"')
    return "".join(rendered)


def _style_classes(styles: dict[str, Any] | None, key: str) -> list[str]:
    if not styles:
        return []
    raw_value = styles.get(key)
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value] if raw_value.strip() else []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if str(item).strip()]
    if isinstance(raw_value, tuple):
        return [str(item) for item in raw_value if str(item).strip()]
    return [str(raw_value)]


def _render_class_attr(classes: list[str] | None) -> str:
    normalized = [item.strip() for item in (classes or []) if item and item.strip()]
    if not normalized:
        return ""
    return f' class="{html.escape(" ".join(normalized), quote=True)}"'


def _append_attr(existing: str, addition: str) -> str:
    return f"{existing}{addition}"
