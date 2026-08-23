"""A table's column widths belong to the document, not to the browser.

Word states a table's grid in ``w:tblGrid``, in twentieths of a point, and every real
template sets it. The extractor used to drop it, leaving CSS auto layout to infer widths
from content - which hands almost all the width to whichever column holds the most prose
and shaves the rest. On the Intel release notes that squeezed the id column below the
width of an id.
"""

from __future__ import annotations

import pytest
from lxml import etree

from app.conversion.docx_extractor import DocxExtractor, TableBlock, TableCellBlock, TableRowBlock
from app.conversion.html_generator import _render_colgroup, ir_to_html

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _table_xml(grid: str, rows: str = "") -> etree._Element:
    return etree.fromstring(f'<w:tbl xmlns:w="{W}">{grid}{rows}</w:tbl>'.encode())


def _grid(*widths: int) -> str:
    columns = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    return f"<w:tblGrid>{columns}</w:tblGrid>"


def _row(cells: int = 3) -> str:
    return "<w:tr>" + "<w:tc><w:p/></w:tc>" * cells + "</w:tr>"


class TestReadTableGrid:
    def test_reads_the_declared_grid_as_fractions_of_the_table(self):
        """The reading pane is not the page the author laid out; only ratios carry over."""
        widths = DocxExtractor()._read_table_grid(_table_xml(_grid(1440, 6480, 1800)))

        assert [round(width, 4) for width in widths] == [0.1481, 0.6667, 0.1852]
        assert sum(widths) == pytest.approx(1.0)

    def test_a_table_without_a_grid_declares_nothing(self):
        assert DocxExtractor()._read_table_grid(_table_xml("")) == []

    def test_a_zero_width_column_invalidates_the_whole_grid(self):
        """A partial grid would misplace every column after the bad one."""
        assert DocxExtractor()._read_table_grid(_table_xml(_grid(1440, 0, 1800))) == []

    def test_an_unparseable_width_invalidates_the_whole_grid(self):
        broken = '<w:tblGrid><w:gridCol w:w="wide"/><w:gridCol w:w="1800"/></w:tblGrid>'

        assert DocxExtractor()._read_table_grid(_table_xml(broken)) == []


class TestGridMatchesTheParsedTable:
    def _parse(self, element):
        import zipfile
        from io import BytesIO

        archive = zipfile.ZipFile(BytesIO(), "w")
        table, _ = DocxExtractor()._parse_table(
            element,
            archive=archive,
            style_definitions={},
            numbering_definitions={},
            image_relationships={},
            starting_image_number=1,
        )
        return table

    def test_keeps_a_grid_that_matches_the_columns_the_rows_span(self):
        table = self._parse(_table_xml(_grid(1440, 6480, 1800), _row(3) + _row(3)))

        assert len(table.column_widths) == 3

    def test_drops_a_grid_that_does_not(self):
        """A grid one column out shifts every cell - worse than no grid at all."""
        table = self._parse(_table_xml(_grid(1440, 6480, 1800, 900), _row(3)))

        assert table.column_widths == []


class TestRenderColgroup:
    def test_restates_the_proportions_in_the_html(self):
        html = _render_colgroup({"column_widths": [0.15, 0.67, 0.18]})

        assert html == (
            "<colgroup>"
            '<col style="width:15.000%" />'
            '<col style="width:67.000%" />'
            '<col style="width:18.000%" />'
            "</colgroup>"
        )

    def test_emits_nothing_when_the_document_declared_no_grid(self):
        assert _render_colgroup({"column_widths": []}) == ""
        assert _render_colgroup({}) == ""
        assert _render_colgroup(None) == ""

    def test_ignores_a_grid_it_cannot_use(self):
        assert _render_colgroup({"column_widths": ["wide", 0.5]}) == ""
        assert _render_colgroup({"column_widths": [0.0, 1.0]}) == ""

    def test_the_table_carries_the_colgroup_before_its_header(self):
        table = TableBlock(
            rows=[TableRowBlock(cells=[TableCellBlock(), TableCellBlock()])],
            has_header_row=True,
            column_widths=[0.25, 0.75],
        )

        html = ir_to_html(DocxExtractor()._build_table_ir(table))

        assert '<table class="extracted-table"><colgroup>' in html
        assert html.index("<colgroup>") < html.index("<thead>")
