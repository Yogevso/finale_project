"""Integration tests for document due date workflow."""

from datetime import date

from app.models import Document


def test_document_due_date_round_trip_and_clear(client, auth_headers, db):
    create_response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={
            "title": "Due date document",
            "description": "Tracks a due date",
            "due_date": "2026-03-18",
            "platform": "Core Platform",
        },
    )
    assert create_response.status_code == 201
    created_payload = create_response.json()
    document_id = created_payload["id"]
    assert created_payload["due_date"] == "2026-03-18"

    update_response = client.put(
        f"/api/v1/documents/{document_id}",
        headers={**auth_headers, "If-Match": created_payload["etag"]},
        json={"due_date": "2026-03-25"},
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["due_date"] == "2026-03-25"

    clear_response = client.put(
        f"/api/v1/documents/{document_id}",
        headers={**auth_headers, "If-Match": updated_payload["etag"]},
        json={"due_date": None},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["due_date"] is None

    document = db.query(Document).filter(Document.id == document_id).first()
    assert document is not None
    assert document.due_date is None


def test_document_due_date_calendar_export_returns_ical(client, auth_headers):
    create_response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={
            "title": "Release readiness checklist",
            "description": "Calendar export coverage",
            "due_date": "2026-04-01",
            "platform": "Core Platform",
        },
    )
    assert create_response.status_code == 201
    document_id = create_response.json()["id"]

    export_response = client.get(
        f"/api/v1/documents/{document_id}/calendar-export",
        headers=auth_headers,
    )
    assert export_response.status_code == 200
    payload = export_response.json()

    assert payload["document_id"] == document_id
    assert payload["due_date"] == "2026-04-01"
    assert payload["filename"].endswith(".ics")
    assert payload["content_type"] == "text/calendar"
    assert "BEGIN:VCALENDAR" in payload["ical"]
    assert "SUMMARY:Release readiness checklist" in payload["ical"]
    assert f"DTSTART;VALUE=DATE:{date(2026, 4, 1).strftime('%Y%m%d')}" in payload["ical"]
