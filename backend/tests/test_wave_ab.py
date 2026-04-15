"""Wave AB – Experimentation & Growth tests (AB-017 → AB-025).

Tests target the *service layer* directly so they run against the
in-memory SQLite DB without needing HTTP auth stubs.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import (
    ExperimentStatus,
    UserRole,
)
from app.services.experimentation_service import (
    assign_user_to_experiment,
    authenticate_api_key,
    check_guardrails,
    create_api_key,
    create_experiment,
    create_webhook,
    delete_webhook,
    get_activation_summary,
    get_churn_risk_users,
    get_experiment,
    get_integration_health,
    get_onboarding_funnel,
    get_retention_cohorts,
    get_user_assignment,
    get_user_milestones,
    get_webhook_delivery_log,
    kill_experiment,
    list_api_keys,
    list_experiments,
    list_feature_flags_for_tenant,
    list_webhooks,
    record_metric_snapshot,
    record_milestone,
    record_onboarding_event,
    revoke_api_key,
    start_experiment,
    stop_experiment,
    update_feature_flag_targeting,
    update_webhook,
)
from tests.factories.domain import create_tenant, create_user

# ───── helpers ─────


def _seed(db: Session):
    """Create a shared tenant + admin user and return (tenant, user)."""
    tenant = create_tenant(db)
    user = create_user(db, tenant_id=tenant.id, role=UserRole.SYSTEM_ADMIN)
    return tenant, user


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-017: Feature-Flag Targeting                               ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestFeatureFlagTargeting:
    def test_create_and_list(self, db: Session):
        tenant, user = _seed(db)

        flag = update_feature_flag_targeting(
            db,
            tenant_id=tenant.id,
            feature_key="dark_mode",
            enabled=True,
            rollout_percentage=50,
            target_tenant_ids=[tenant.id],
            updated_by=user.id,
        )
        assert flag.feature_key == "dark_mode"
        assert flag.rollout_percentage == 50
        assert flag.enabled is True

        flags = list_feature_flags_for_tenant(db, tenant.id)
        assert any(f.feature_key == "dark_mode" for f in flags)

    def test_update_existing(self, db: Session):
        tenant, user = _seed(db)

        update_feature_flag_targeting(
            db,
            tenant_id=tenant.id,
            feature_key="beta_ui",
            enabled=True,
            rollout_percentage=100,
            updated_by=user.id,
        )
        updated = update_feature_flag_targeting(
            db,
            tenant_id=tenant.id,
            feature_key="beta_ui",
            enabled=False,
            rollout_percentage=25,
            updated_by=user.id,
        )
        assert updated.enabled is False
        assert updated.rollout_percentage == 25


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-018: Experiment Lifecycle                                 ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestExperimentLifecycle:
    def test_create_start_stop(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Sign-up Button Colour",
            description="A/B test for sign-up CTA",
            feature_flag_key="signup_colour",
            variants=["control", "green", "blue"],
            traffic_percentage=80,
            primary_metric="conversion_rate",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        assert exp.status == ExperimentStatus.DRAFT

        started = start_experiment(db, exp.id)
        assert started.status == ExperimentStatus.RUNNING
        assert started.started_at is not None

        stopped = stop_experiment(db, exp.id)
        assert stopped.status == ExperimentStatus.COMPLETED
        assert stopped.ended_at is not None

    def test_list_and_get(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Pricing Page",
            feature_flag_key="pricing_v2",
            variants=["control", "variant_a"],
            traffic_percentage=50,
            primary_metric="revenue",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        found = get_experiment(db, exp.id)
        assert found is not None
        assert found.name == "Pricing Page"

        exps = list_experiments(db)
        assert any(e.name == "Pricing Page" for e in exps)

    def test_kill_experiment(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Kill Test",
            feature_flag_key="kill_flag",
            variants=["control", "variant"],
            traffic_percentage=100,
            primary_metric="clicks",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        start_experiment(db, exp.id)
        killed = kill_experiment(db, exp.id, "control")
        assert killed.status == ExperimentStatus.COMPLETED
        assert killed.winner_variant == "control"


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-019: Experiment Assignment & Metrics                      ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestAssignmentAndMetrics:
    def test_deterministic_assignment(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Deterministic",
            feature_flag_key="determ",
            variants=["control", "treatment"],
            traffic_percentage=100,
            primary_metric="ctr",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        start_experiment(db, exp.id)

        a1 = assign_user_to_experiment(db, exp.id, user.id)
        a2 = get_user_assignment(db, exp.id, user.id)
        assert a2 is not None
        assert a1.variant == a2.variant

    def test_record_metric(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Metric Test",
            feature_flag_key="metric_flag",
            variants=["control", "treatment"],
            traffic_percentage=100,
            primary_metric="conversion",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        start_experiment(db, exp.id)

        snap = record_metric_snapshot(
            db,
            experiment_id=exp.id,
            variant="control",
            metric_name="conversion",
            metric_value=0.12,
            sample_size=100,
        )
        assert float(snap.metric_value) == pytest.approx(0.12)
        assert snap.sample_size == 100

    def test_guardrails(self, db: Session):
        tenant, user = _seed(db)

        exp = create_experiment(
            db,
            name="Guardrail Test",
            feature_flag_key="guard_flag",
            variants=["control", "treatment"],
            traffic_percentage=100,
            primary_metric="conversion",
            guardrail_metrics=["latency"],
            guardrail_threshold=0.20,
            created_by=user.id,
            tenant_id=tenant.id,
        )
        start_experiment(db, exp.id)

        record_metric_snapshot(db, exp.id, "control", "latency", 100.0, 50)
        record_metric_snapshot(db, exp.id, "treatment", "latency", 150.0, 50)

        result = check_guardrails(db, exp.id)
        assert isinstance(result, dict)
        assert "ok" in result
        assert "violations" in result


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-020: Onboarding Funnel                                    ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestOnboardingFunnel:
    def test_record_and_funnel(self, db: Session):
        tenant, user = _seed(db)

        record_onboarding_event(db, user.id, tenant.id, "invitation_sent")
        record_onboarding_event(db, user.id, tenant.id, "accepted")
        record_onboarding_event(db, user.id, tenant.id, "first_login")

        funnel = get_onboarding_funnel(db, tenant.id)
        assert isinstance(funnel, list)
        assert len(funnel) > 0
        # First step (invitation_sent) should have count >= 1
        assert funnel[0]["count"] >= 1


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-021: Activation Milestones                                ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestActivationMilestones:
    def test_record_and_get(self, db: Session):
        tenant, user = _seed(db)

        record_milestone(db, user.id, tenant.id, "first_document")
        record_milestone(db, user.id, tenant.id, "first_share")

        milestones = get_user_milestones(db, user.id)
        names = [m.milestone for m in milestones]
        assert "first_document" in names
        assert "first_share" in names

    def test_activation_summary(self, db: Session):
        tenant, user = _seed(db)

        record_milestone(db, user.id, tenant.id, "first_document")

        summary = get_activation_summary(db, tenant.id)
        assert isinstance(summary, list)


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-022: Retention Cohorts                                    ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestRetentionCohorts:
    def test_returns_list(self, db: Session):
        tenant, _ = _seed(db)

        result = get_retention_cohorts(db, tenant.id, weeks=4)
        assert isinstance(result, list)


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-023: Churn Prediction                                     ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestChurnPrediction:
    def test_returns_structure(self, db: Session):
        tenant, _ = _seed(db)

        result = get_churn_risk_users(db, tenant.id, inactive_days=30)
        assert "at_risk_users" in result
        assert "total_active" in result
        assert "total_at_risk" in result


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-024: Webhooks & API Keys                                  ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestWebhooks:
    def test_crud_lifecycle(self, db: Session):
        tenant, user = _seed(db)

        wh, secret = create_webhook(
            db,
            tenant_id=tenant.id,
            url="https://example.com/hook",
            event_types=["document.created", "document.updated"],
            created_by=user.id,
        )
        assert wh.url == "https://example.com/hook"
        assert secret  # non-empty

        hooks = list_webhooks(db, tenant.id)
        assert len(hooks) >= 1

        updated = update_webhook(db, wh.id, tenant.id, url="https://new.example.com/hook")
        assert updated.url == "https://new.example.com/hook"

        assert delete_webhook(db, wh.id, tenant.id) is True
        hooks_after = list_webhooks(db, tenant.id)
        assert len(hooks_after) == 0

    def test_delivery_log(self, db: Session):
        tenant, user = _seed(db)

        wh, _ = create_webhook(
            db,
            tenant_id=tenant.id,
            url="https://example.com/hook",
            event_types=["test.event"],
            created_by=user.id,
        )
        log = get_webhook_delivery_log(db, wh.id, tenant.id)
        assert "deliveries" in log
        assert "success_rate" in log


class TestApiKeys:
    def test_create_list_revoke(self, db: Session):
        tenant, user = _seed(db)

        key, raw = create_api_key(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            name="CI Pipeline",
            scopes=["read", "write"],
            expires_in_days=90,
        )
        assert raw.startswith(key.key_prefix)
        assert key.is_active is True

        keys = list_api_keys(db, tenant.id)
        assert any(k.name == "CI Pipeline" for k in keys)

        assert revoke_api_key(db, key.id, tenant.id) is True
        keys_after = list_api_keys(db, tenant.id)
        assert all(k.is_active is False for k in keys_after if k.name == "CI Pipeline")

    def test_authenticate(self, db: Session):
        tenant, user = _seed(db)

        key, raw = create_api_key(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            name="Auth Test",
            scopes=["read"],
        )
        authed = authenticate_api_key(db, raw)
        assert authed is not None
        assert authed.id == key.id

        # Bad key
        assert authenticate_api_key(db, "invalid-key-000000") is None


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-025: Integration Health                                   ║
# ╚═══════════════════════════════════════════════════════════════╝


class TestIntegrationHealth:
    def test_returns_structure(self, db: Session):
        tenant, user = _seed(db)

        # Seed some data to make the health endpoint meaningful
        create_webhook(
            db,
            tenant_id=tenant.id,
            url="https://example.com/health",
            event_types=["test"],
            created_by=user.id,
        )
        create_api_key(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            name="Health Key",
        )

        health = get_integration_health(db, tenant.id)
        assert "webhooks" in health
        assert "api_keys" in health
        assert health["webhooks"]["total"] >= 1
        assert health["api_keys"]["active"] >= 1
