"""Audience query benchmark scenario for Wave V performance guardrails."""

from __future__ import annotations

import json
from datetime import datetime
from time import perf_counter

import pytest
from sqlalchemy import func

from app.config import settings
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    UserRole,
    document_company_assignments,
)
from app.search_backend import database_dialect_name, resolve_search_backend_mode
from tests.factories import create_tenant, create_user

BENCHMARK_DOCUMENT_COUNT = 10_000
BENCHMARK_ITERATIONS = 15


def _percentiles(latencies_ms: list[float]) -> tuple[float, float]:
    ordered = sorted(latencies_ms)
    if not ordered:
        return (0.0, 0.0)

    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 0:
        p50 = (ordered[midpoint - 1] + ordered[midpoint]) / 2
    else:
        p50 = ordered[midpoint]
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return p50, ordered[p95_index]


def _measure_latency_ms(action, *, iterations: int) -> list[float]:
    samples: list[float] = []
    for _ in range(iterations):
        started_at = perf_counter()
        response = action()
        elapsed_ms = (perf_counter() - started_at) * 1000.0
        assert response.status_code == 200
        samples.append(elapsed_ms)
    return samples


def _seed_benchmark_dataset(
    db,
    *,
    author_id: int,
    author_tenant_id: int,
    customer_company_id: int,
) -> int:
    now = datetime.utcnow()
    max_existing_id = int(db.query(func.max(Document.id)).scalar() or 0)
    rows: list[dict[str, object]] = []
    company_document_ids: list[int] = []

    for index in range(BENCHMARK_DOCUMENT_COUNT):
        document_id = max_existing_id + index + 1
        visibility = (
            DocumentVisibility.COMPANY if index % 5 == 0 else DocumentVisibility.INTERNAL
        )
        if visibility == DocumentVisibility.COMPANY:
            company_document_ids.append(document_id)

        rows.append(
            {
                "id": document_id,
                "tenant_id": author_tenant_id,
                "title": f"Benchmark Document {index:05d}",
                "document_number": f"DOC-BENCH-{document_id:06d}",
                "description": "Benchmark payload for audience query latency",
                "status": DocumentStatus.ACTIVE,
                "visibility": visibility,
                "category": "Benchmark",
                "topic": None,
                "platform": None,
                "platform_id": None,
                "release_branch": None,
                "tags": "benchmark,audience,perf",
                "thumbnail_url": None,
                "yjs_state": None,
                "created_by": author_id,
                "parent_id": None,
                "row_version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )

    db.bulk_insert_mappings(Document, rows)
    db.execute(
        document_company_assignments.insert(),
        [
            {
                "document_id": document_id,
                "tenant_id": customer_company_id,
                "assigned_by": author_id,
                "assigned_at": now,
            }
            for document_id in company_document_ids
        ],
    )
    db.commit()
    return company_document_ids[0]


@pytest.mark.slow
@pytest.mark.integration
def test_audience_query_benchmarks(client, db, test_admin, record_property):
    """
    Measure p50/p95 latency for core audience query paths on a 10K document dataset.
    """
    customer_company = create_tenant(
        db,
        name="Benchmark Customer",
        slug="benchmark-customer",
        company_type="customer",
    )
    customer_user = create_user(
        db,
        email="benchmark-customer@example.com",
        username="benchmark_customer",
        full_name="Benchmark Customer",
        plain_password="bench-pass-123",
        role=UserRole.CUSTOMER,
        tenant_id=customer_company.id,
    )
    _ = customer_user

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": test_admin.username, "password": "admin123"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    benchmark_document_id = _seed_benchmark_dataset(
        db,
        author_id=test_admin.id,
        author_tenant_id=test_admin.tenant_id,
        customer_company_id=customer_company.id,
    )

    assignment_list_samples = _measure_latency_ms(
        lambda: client.get(
            f"/api/v1/documents/{benchmark_document_id}/assigned-companies",
            headers=admin_headers,
        ),
        iterations=BENCHMARK_ITERATIONS,
    )
    detail_samples = _measure_latency_ms(
        lambda: client.get(
            f"/api/v1/documents/{benchmark_document_id}",
            headers=admin_headers,
        ),
        iterations=BENCHMARK_ITERATIONS,
    )
    search_samples = _measure_latency_ms(
        lambda: client.get(
            "/api/v1/search/?q=Benchmark&page=1&page_size=20",
            headers=admin_headers,
        ),
        iterations=BENCHMARK_ITERATIONS,
    )

    assignment_p50, assignment_p95 = _percentiles(assignment_list_samples)
    detail_p50, detail_p95 = _percentiles(detail_samples)
    search_p50, search_p95 = _percentiles(search_samples)
    search_backend_mode = resolve_search_backend_mode(
        settings.SEARCH_BACKEND_MODE,
        dialect_name=database_dialect_name(db),
    )

    metrics = {
        "assignment_list": {"p50_ms": assignment_p50, "p95_ms": assignment_p95},
        "document_detail_with_companies": {"p50_ms": detail_p50, "p95_ms": detail_p95},
        "search_with_audience_filter": {
            "backend_mode": search_backend_mode.value,
            "p50_ms": search_p50,
            "p95_ms": search_p95,
        },
    }
    for metric in metrics.values():
        assert metric["p50_ms"] >= 0.0
        assert metric["p95_ms"] >= metric["p50_ms"]

    record_property("audience_benchmark_metrics", metrics)
    record_property("audience_benchmark_metrics_json", json.dumps(metrics, sort_keys=True))
