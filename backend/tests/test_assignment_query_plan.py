"""Regression checks for assignment index presence and query-plan usage."""

from sqlalchemy import text


def test_document_company_assignment_index_exists_and_explain_uses_index(db):
    index_rows = db.execute(text("PRAGMA index_list('document_company_assignments')")).fetchall()
    index_names = {str(row[1]) for row in index_rows}
    assert "ix_document_company_assignments_document_id_tenant_id" in index_names

    explain_rows = db.execute(
        text(
            """
            EXPLAIN QUERY PLAN
            SELECT document_id
            FROM document_company_assignments
            WHERE document_id = :document_id AND tenant_id = :tenant_id
            """
        ),
        {"document_id": 1, "tenant_id": 1},
    ).fetchall()
    detail = " ".join(str(row[3]).upper() for row in explain_rows)
    assert "INDEX" in detail
