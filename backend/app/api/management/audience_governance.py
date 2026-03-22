"""Audience governance endpoints: audit export, alert rules, and access history."""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_admin, require_manager
from app.dependencies.services import get_analytics_service
from app.errors.audience_errors import AudienceErrorCode
from app.legacy_wrappers import AnalyticsServiceStranglerWrapper
from app.models import ActionType, SystemSetting, User, UserRole
from app.services.audit_helper import write_audit_log

router = APIRouter()

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALERT_RULES_SETTING_KEY = "audience_alert_rules"


class AudienceAlertRuleCreate(BaseModel):
    metric: str = Field(..., min_length=3, max_length=120)
    threshold: int = Field(..., ge=1, le=1000000)
    window_minutes: int = Field(..., ge=1, le=10080)
    document_id: int | None = None
    enabled: bool = True


class AudienceAlertRule(BaseModel):
    id: str
    metric: str
    threshold: int
    window_minutes: int
    document_id: int | None = None
    enabled: bool = True
    created_at: str
    updated_at: str


def _redact_pii(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = EMAIL_PATTERN.sub("[redacted-email]", value)
    redacted = IP_PATTERN.sub("[redacted-ip]", redacted)
    return redacted


def _apply_audit_redaction(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted_rows: list[dict[str, Any]] = []
    for row in rows:
        redacted_rows.append(
            {
                **row,
                "user_email": _redact_pii(row.get("user_email")),
                "ip_address": "[redacted-ip]" if row.get("ip_address") else None,
                "details": _redact_pii(row.get("details")),
            }
        )
    return redacted_rows


@router.get("/audit/export")
def export_audit_logs(
    format: Literal["json", "csv"] = Query("json"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: User = Depends(require_manager),
    analytics_service: AnalyticsServiceStranglerWrapper = Depends(get_analytics_service),
):
    """
    Export audit logs in JSON or CSV.

    Non-system-admin callers receive redacted PII fields.
    """
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
            headers={"X-Error-Code": AudienceErrorCode.AUDIENCE_020.name},
        )

    rows = analytics_service.export_audit_logs(date_from=date_from, date_to=date_to)
    should_redact = current_user.role != UserRole.SYSTEM_ADMIN
    export_rows = _apply_audit_redaction(rows) if should_redact else rows

    if format == "json":
        return {"items": export_rows, "total": len(export_rows), "redacted": should_redact}

    output = io.StringIO()
    fieldnames = [
        "id",
        "created_at",
        "user_id",
        "user_email",
        "document_id",
        "document_title",
        "action",
        "audience_event_type",
        "details",
        "assignment_diff",
        "ip_address",
        "signature_key_id",
        "signature",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in export_rows:
        writer.writerow({field: row.get(field) for field in fieldnames})
    filename = f"audit-export-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _load_alert_rules(db: Session) -> list[dict[str, Any]]:
    row = db.query(SystemSetting).filter(SystemSetting.key == ALERT_RULES_SETTING_KEY).first()
    if not row or not row.value:
        return []
    try:
        parsed = json.loads(row.value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _save_alert_rules(db: Session, *, rules: list[dict[str, Any]], updated_by: int | None) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == ALERT_RULES_SETTING_KEY).first()
    encoded = json.dumps(rules, sort_keys=True)
    if row:
        row.value = encoded
        row.updated_by = updated_by
    else:
        row = SystemSetting(key=ALERT_RULES_SETTING_KEY, value=encoded, updated_by=updated_by)
        db.add(row)
    db.commit()


@router.get("/admin/alerts/audience-rules", response_model=list[AudienceAlertRule])
def list_audience_alert_rules(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = current_user
    rules = _load_alert_rules(db)
    return [AudienceAlertRule.model_validate(rule) for rule in rules]


@router.post("/admin/alerts/audience-rules", response_model=AudienceAlertRule)
def create_audience_alert_rule(
    payload: AudienceAlertRuleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow().isoformat()
    rules = _load_alert_rules(db)
    created = AudienceAlertRule(
        id=f"audience-rule-{uuid.uuid4().hex[:10]}",
        metric=payload.metric,
        threshold=payload.threshold,
        window_minutes=payload.window_minutes,
        document_id=payload.document_id,
        enabled=payload.enabled,
        created_at=now,
        updated_at=now,
    )
    rules.append(created.model_dump())
    _save_alert_rules(db, rules=rules, updated_by=current_user.id)

    write_audit_log(
        user_id=current_user.id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {"event": "audience_alert_rule_created", "rule_id": created.id},
            sort_keys=True,
        ),
    )
    return created


@router.delete("/admin/alerts/audience-rules/{rule_id}")
def delete_audience_alert_rule(
    rule_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rules = _load_alert_rules(db)
    remaining = [rule for rule in rules if rule.get("id") != rule_id]
    if len(remaining) == len(rules):
        raise HTTPException(status_code=404, detail="Audience alert rule not found")

    _save_alert_rules(db, rules=remaining, updated_by=current_user.id)
    write_audit_log(
        user_id=current_user.id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {"event": "audience_alert_rule_deleted", "rule_id": rule_id},
            sort_keys=True,
        ),
    )
    return {"message": "Audience alert rule deleted", "rule_id": rule_id}


@router.get("/admin/access-history/{company_id}")
def get_company_access_history(
    company_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: User = Depends(require_manager),
    analytics_service: AnalyticsServiceStranglerWrapper = Depends(get_analytics_service),
):
    """
    Timeline of document access gain/loss events for one company.
    """
    tenant_ctx = analytics_service.tenant_ctx
    if (
        current_user.role != UserRole.SYSTEM_ADMIN
        and tenant_ctx
        and not tenant_ctx.is_system_admin
        and tenant_ctx.tenant_id != company_id
    ):
        raise HTTPException(status_code=403, detail="Company scope denied")

    if not date_from:
        date_from = date.today() - timedelta(days=90)
    if not date_to:
        date_to = date.today()

    rows = analytics_service.export_audit_logs(date_from=date_from, date_to=date_to)
    should_redact = current_user.role != UserRole.SYSTEM_ADMIN
    timeline: list[dict[str, Any]] = []
    for row in rows:
        raw_diff = row.get("assignment_diff")
        if not raw_diff:
            continue
        try:
            diff = json.loads(raw_diff)
        except json.JSONDecodeError:
            continue
        added_ids = set(diff.get("added_company_ids", []))
        removed_ids = set(diff.get("removed_company_ids", []))
        event_type = None
        if company_id in added_ids:
            event_type = "gained_access"
        elif company_id in removed_ids:
            event_type = "lost_access"
        if not event_type:
            continue
        timeline.append(
            {
                "timestamp": row.get("created_at"),
                "document_id": row.get("document_id"),
                "document_title": row.get("document_title"),
                "event_type": event_type,
                "actor_user_id": row.get("user_id"),
                "actor_user_email": (
                    _redact_pii(row.get("user_email")) if should_redact else row.get("user_email")
                ),
            }
        )

    timeline.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return {
        "company_id": company_id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "events": timeline,
        "total": len(timeline),
    }
