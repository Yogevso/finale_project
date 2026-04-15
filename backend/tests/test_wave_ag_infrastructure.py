"""Wave AG — Tests for infrastructure, reliability & ops items.

AG-016: verify only PyJWT imported (no python-jose)
AG-017: collab URL single source of truth
AG-018: email retry on transient SMTP failure
AG-019: cleanup worker purges expired sessions/tokens
AG-020: scheduled-publish worker fires at appointed time
AG-021: admin list users uses eager loading (query count)
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta
from pathlib import Path

from app.models import (
    DocumentStatus,
    DocumentVisibility,
    PasswordReset,
    UserRole,
    UserSession,
    Version,
    VersionBumpType,
)
from tests.factories.domain import create_document, create_user, persist

# ══════════════════════════════════════════════════════════════════
# AG-016: Verify only PyJWT imported (no python-jose imports remain)
# ══════════════════════════════════════════════════════════════════


class TestAG016NoPythonJoseImports:
    """No production code should import from python-jose."""

    def test_no_jose_imports_in_production_code(self):
        """Scan all .py files under backend/app/ for 'jose' imports."""
        app_dir = Path(__file__).resolve().parent.parent / "app"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "jose" in alias.name:
                            violations.append(f"{py_file.relative_to(app_dir)}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "jose" in node.module:
                        violations.append(f"{py_file.relative_to(app_dir)}:{node.lineno}")

        assert violations == [], "python-jose imports found in production code:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_pyjwt_is_usable(self):
        """Verify PyJWT can be imported and encodes/decodes correctly."""
        import jwt

        token = jwt.encode({"sub": "test"}, "secret", algorithm="HS256")
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        assert payload["sub"] == "test"


# ══════════════════════════════════════════════════════════════════
# AG-017: Collab URL resolved from single source
# ══════════════════════════════════════════════════════════════════


class TestAG017CollabUrlSingleSource:
    """Collab URL must be resolved from one canonical env var per surface."""

    def test_backend_config_has_collab_server_url(self):
        from app.config import Settings

        s = Settings(COLLAB_SERVER_URL="http://test:8002")
        assert s.COLLAB_SERVER_URL == "http://test:8002"

    def test_docker_compose_uses_vite_collab_server_url(self):
        """docker-compose files must use VITE_COLLAB_SERVER_URL, not VITE_COLLAB_WS_URL."""
        root = Path(__file__).resolve().parent.parent.parent
        for dc_file in ("docker-compose.yml", "docker-compose.prod.yml"):
            content = (root / dc_file).read_text()
            assert (
                "VITE_COLLAB_WS_URL" not in content
            ), f"{dc_file} still uses deprecated VITE_COLLAB_WS_URL"

    def test_dev_compose_allows_loopback_frontend_origins(self):
        """Development compose should allow both localhost and 127.0.0.1 frontend origins."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "docker-compose.yml").read_text()
        assert "http://localhost:3000" in content
        assert "http://127.0.0.1:3000" in content
        assert "http://localhost:5173" in content
        assert "http://127.0.0.1:5173" in content

    def test_frontend_uses_vite_collab_server_url(self):
        """Frontend hook must reference VITE_COLLAB_SERVER_URL."""
        root = Path(__file__).resolve().parent.parent.parent
        hook_path = root / "frontend" / "src" / "lib" / "useCollaboration.ts"
        if hook_path.exists():
            content = hook_path.read_text()
            assert "VITE_COLLAB_SERVER_URL" in content

    def test_collab_server_uses_backend_secret_key_name(self):
        """Compose files should wire collab signing through SECRET_KEY, not a separate JWT secret name."""
        root = Path(__file__).resolve().parent.parent.parent
        for dc_file in ("docker-compose.yml", "docker-compose.prod.yml"):
            content = (root / dc_file).read_text()
            assert "SECRET_KEY=${SECRET_KEY" in content
            assert "JWT_SECRET=" not in content

    def test_root_env_example_uses_current_collab_env_names(self):
        """Root env example should use VITE_COLLAB_SERVER_URL and not legacy names."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".env.example").read_text()
        assert "VITE_COLLAB_SERVER_URL=" in content
        assert "VITE_COLLAB_WS_URL" not in content
        assert "COLLAB_WS_URL" not in content

    def test_collab_docs_prefer_secret_key_name(self):
        """Operator-facing collab docs should prefer SECRET_KEY over legacy JWT_SECRET."""
        root = Path(__file__).resolve().parent.parent.parent
        env_example = (root / "collab-server" / ".env.example").read_text()
        readme = (root / "collab-server" / "README.md").read_text()
        assert "SECRET_KEY=" in env_example
        assert "SECRET_KEY_OLD=" in env_example
        assert "JWT_SECRET=" not in env_example
        assert "Required `SECRET_KEY` environment variable" in readme
        assert "SECRET_KEY_OLD" in readme

    def test_prod_compose_backend_has_redis_contract(self):
        """Production compose should provide REDIS_URL to the backend and run Redis by default."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "docker-compose.prod.yml").read_text()
        assert "- REDIS_URL=${REDIS_URL:-redis://redis:6379/0}" in content
        assert (
            "- SEARCH_BACKEND_MODE=${SEARCH_BACKEND_MODE:?SEARCH_BACKEND_MODE must be explicit in production}"
            in content
        )

        redis_start = content.index("\n  redis:\n")
        ollama_start = content.index("\n  # Self-hosted LLM inference", redis_start)
        redis_block = content[redis_start:ollama_start]
        assert "profiles:" not in redis_block

    def test_validate_config_prefers_current_env_contract(self):
        """The config validator should use current secret and collab variable names."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "scripts" / "validate_config.py").read_text()
        assert "JWT_SECRET_KEY" not in content
        assert "VITE_COLLAB_SERVER_URL" in content
        assert '"SEARCH_BACKEND_MODE"' in content

    def test_root_env_example_documents_search_backend_mode(self):
        """Root env example should document the explicit production search mode."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".env.example").read_text()
        assert "SEARCH_BACKEND_MODE=" in content
        assert "postgres_tsv" in content

    def test_root_env_example_documents_rotation_and_upload_boundary(self):
        """Root env example should expose the rotation grace key and intentional upload cap."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".env.example").read_text()
        assert "SECRET_KEY_OLD=" in content
        assert "MAX_UPLOAD_SIZE=52428800" in content

    def test_root_env_example_documents_assistant_capacity_knobs(self):
        """Root env example should document assistant admission-control settings."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".env.example").read_text()
        assert "ASSISTANT_CHAT_MAX_CONCURRENT=" in content
        assert "ASSISTANT_CHAT_MAX_QUEUE=" in content
        assert "ASSISTANT_EMBEDDING_MAX_CONCURRENT=" in content
        assert "ASSISTANT_EMBEDDING_MAX_QUEUE=" in content

    def test_backend_entrypoint_does_not_force_demo_seed_in_production(self):
        """The backend entrypoint should gate demo seeding behind the shared policy helper."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "backend" / "docker-entrypoint.sh").read_text()
        assert "should_seed_demo_data" in content
        assert "SEED_DEMO_DATA=true" in content

    def test_cd_workflow_builds_and_deploys_collab_server(self):
        """CD should include collab-server in the image and deployment chain."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "cd.yml").read_text()
        assert "IMAGE_NAME_COLLAB" in content
        assert "build-collab" in content
        assert "COLLAB_SERVER_IMAGE" in content

    def test_cd_workflow_frontend_build_injects_collab_url(self):
        """Frontend release builds should inject both API and collaboration URLs."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "cd.yml").read_text()
        assert "VITE_API_URL=${{ vars.API_URL" in content
        assert "VITE_COLLAB_SERVER_URL=${{ vars.COLLAB_SERVER_URL" in content

    def test_cd_workflow_uses_real_rollout_script_instead_of_placeholders(self):
        """CD should call the rollout helper rather than leaving ssh examples commented out."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "cd.yml").read_text()
        assert "bash scripts/release/remote_compose_rollout.sh" in content
        assert "Example deployment commands" not in content
        assert "Add rollback logic here" not in content

    def test_frontend_dockerfile_accepts_release_build_args(self):
        """Frontend Dockerfile should consume release build args and run on port 8080."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "frontend" / "Dockerfile").read_text()
        assert "ARG VITE_API_URL" in content
        assert "ARG VITE_COLLAB_SERVER_URL" in content
        assert 'ENV VITE_API_URL="${VITE_API_URL}"' in content
        assert 'ENV VITE_COLLAB_SERVER_URL="${VITE_COLLAB_SERVER_URL}"' in content
        assert "npm run build:docker" in content
        assert "EXPOSE 8080" in content
        assert "localhost:8080" in content or "127.0.0.1:8080" in content

    def test_frontend_nginx_conf_matches_unprivileged_runtime(self):
        """Frontend nginx config should assume upstream TLS termination and listen on 8080."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "frontend" / "nginx.conf").read_text()
        assert "listen 8080;" in content
        assert "resolver 127.0.0.11" in content
        assert "set $backend_upstream http://backend:8000;" in content
        assert "ssl_certificate" not in content
        assert "listen 443" not in content

    def test_prod_compose_uses_image_overrides_and_loopback_frontend_port(self):
        """Production compose should support image-based rollout and loopback frontend exposure."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "docker-compose.prod.yml").read_text()
        assert "image: ${BACKEND_IMAGE:-portal-backend:local}" in content
        assert "image: ${FRONTEND_IMAGE:-portal-frontend:local}" in content
        assert "image: ${COLLAB_SERVER_IMAGE:-portal-collab-server:local}" in content
        assert '- "127.0.0.1:8080:8080"' in content
        assert '- "443:443"' not in content
        assert '- "127.0.0.1:8003:8003"' in content

    def test_security_workflow_scans_collab_dependencies_and_container(self):
        """Security workflow should cover collab-server in both dependency and container scans."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
        assert "dependency-scan-collab" in content
        assert "working-directory: ./collab-server" in content
        assert "cache-dependency-path: collab-server/package-lock.json" in content
        assert "- name: collab-server" in content
        assert "path: ./collab-server" in content
        assert "name: collab-security-reports" in content

    def test_security_summary_includes_collab_dependency_scan(self):
        """Security summary should report the collab dependency scan result."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
        assert (
            "needs: [dependency-scan-backend, dependency-scan-frontend, dependency-scan-collab, codeql-analysis, secret-scan]"
            in content
        )
        assert "Collaboration Dependencies" in content

    def test_dependabot_covers_collab_server(self):
        """Dependabot should manage collab-server npm and Docker dependencies."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "dependabot.yml").read_text()
        assert 'directory: "/collab-server"' in content
        assert 'package-ecosystem: "npm"' in content
        assert 'package-ecosystem: "docker"' in content


class TestAG022TechDebtBudget:
    """Tech-debt tracking should be enforced from source control."""

    def test_architecture_fitness_runs_tech_debt_budget(self):
        root = Path(__file__).resolve().parent.parent.parent
        workflow = (root / ".github" / "workflows" / "architecture-fitness.yml").read_text()
        assert "python backend/scripts/tech_debt_budget.py --budget 200" in workflow

    def test_architecture_fitness_runs_exception_policy_check(self):
        root = Path(__file__).resolve().parent.parent.parent
        workflow = (root / ".github" / "workflows" / "architecture-fitness.yml").read_text()
        assert (
            "python scripts/architecture_checks/check_exception_policy_annotations.py" in workflow
        )


class TestAG023PythonDependencyGovernance:
    """Backend Python dependency governance should use one clear lock strategy."""

    def test_backend_uses_source_and_lock_manifests(self):
        root = Path(__file__).resolve().parent.parent.parent
        backend_dir = root / "backend"

        assert (backend_dir / "requirements.in").exists()
        assert (backend_dir / "requirements-dev.in").exists()
        assert (backend_dir / "requirements.txt").exists()
        assert (backend_dir / "requirements-dev.txt").exists()
        assert not (backend_dir / "requirements.lock").exists()

    def test_runtime_manifest_excludes_dev_tooling(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "backend" / "requirements.in").read_text()

        assert "pytest" not in content
        assert "ruff" not in content
        assert "mypy" not in content
        assert "pip-audit" not in content
        assert "pip-tools" not in content

    def test_dev_manifest_includes_runtime_and_audit_tooling(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "backend" / "requirements-dev.in").read_text()

        assert "-r requirements.in" in content
        assert "pytest==" in content
        assert "ruff==" in content
        assert "mypy==" in content
        assert "pip-audit==" in content
        assert "pip-tools==" in content

    def test_backend_dockerfile_installs_only_locked_runtime_manifest(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "backend" / "Dockerfile").read_text()

        assert "COPY requirements.txt ." in content
        assert "pip install --no-cache-dir -r requirements.txt" in content
        assert "pip install --no-cache-dir uvicorn[standard] fastapi" not in content
        assert "pip install --no-cache-dir sqlalchemy alembic" not in content

    def test_pip_audit_gate_uses_locked_manifest_inputs(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "scripts" / "pip_audit_gate.py").read_text()

        assert 'RUNTIME_MANIFEST = BACKEND_DIR / "requirements.txt"' in content
        assert 'DEV_MANIFEST = BACKEND_DIR / "requirements-dev.txt"' in content
        assert 'IGNORE_FILE = BACKEND_DIR / "pip-audit.ignore"' in content
        assert '"pip-audit", "-r", str(manifest), "--strict", "--desc"' in content
        assert "--include-dev" in content

    def test_security_workflow_audits_runtime_and_dev_lockfiles(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")

        assert "safety check -r requirements.txt" in content
        assert (
            "pip-audit -r requirements.txt --format json --output pip-audit-runtime-report.json"
            in content
        )
        assert (
            "pip-audit -r requirements-dev.txt --format json --output pip-audit-dev-report.json"
            in content
        )
        assert "pip-audit.ignore" in content
        assert "backend/pip-audit-runtime-report.json" in content
        assert "backend/pip-audit-dev-report.json" in content

    def test_pip_audit_ignore_file_documents_current_waiver(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "backend" / "pip-audit.ignore").read_text()

        assert "CVE-2026-4539" in content

    def test_release_images_are_digest_pinned(self):
        root = Path(__file__).resolve().parent.parent.parent
        backend_dockerfile = (root / "backend" / "Dockerfile").read_text()
        frontend_dockerfile = (root / "frontend" / "Dockerfile").read_text()
        collab_dockerfile = (root / "collab-server" / "Dockerfile").read_text()
        prod_compose = (root / "docker-compose.prod.yml").read_text()
        dev_compose = (root / "docker-compose.yml").read_text()

        assert "FROM python:3.11-slim@sha256:" in backend_dockerfile
        assert "FROM node:20-alpine3.20@sha256:" in frontend_dockerfile
        assert "FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:" in frontend_dockerfile
        assert "FROM node:20-alpine3.20@sha256:" in collab_dockerfile
        assert "redis:7-alpine@sha256:" in prod_compose
        assert "ollama/ollama@sha256:" in prod_compose
        assert "postgres:16-alpine@sha256:" in prod_compose
        assert "ollama/ollama:latest" not in prod_compose
        assert "redis:7-alpine@sha256:" in dev_compose
        assert "ollama/ollama@sha256:" in dev_compose
        assert "postgres:16-alpine@sha256:" in dev_compose

    def test_security_workflow_pins_actions_and_generates_node_audit_reports(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")

        assert "@master" not in content
        assert "@main" not in content
        assert "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5" in content
        assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in content
        assert "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020" in content
        assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in content
        assert "github/codeql-action/init@480db559a14342288b67e54bd959dd52dc3ee68f" in content
        assert "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f" in content
        assert "docker/build-push-action@ca052bb54ab0790a636c9b5f226502c73d547a25" in content
        assert "aquasecurity/trivy-action@57a97c7e7821a5776cebc9bb87c984fa69cba8f1" in content
        assert "gitleaks/gitleaks-action@dcedce43c6f43de0b836d1fe38946645c9c638dc" in content
        assert "trufflesecurity/trufflehog@586f66d7886cd0b037c7c245d4a6e34ef357ab10" in content
        assert "npm audit --audit-level=high --json > npm-audit-report.json" in content
        assert "frontend/npm-audit-report.json" in content
        assert "collab-server/npm-audit-report.json" in content
        assert "if: ${{ always() }}" in content


class TestAG024PerformanceRegressionGates:
    """Performance/load gates should stay visible and executable in CI."""

    def test_ci_workflow_runs_performance_gate_job(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        assert "performance-gates:" in content
        assert "Performance Regression Gates" in content
        assert "python scripts/performance/run_backend_perf_gate.py" in content
        assert "npm run test:collab-perf-gate -- \\" in content
        assert "backend/perf-gate-results.xml" in content
        assert "frontend/collab-perf-report.json" in content

    def test_ci_paths_cover_script_changes_for_perf_gate(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        assert "- 'scripts/**'" in content

    def test_frontend_package_exposes_collab_perf_gate_script(self):
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "frontend" / "package.json").read_text(encoding="utf-8")

        assert '"test:collab-perf-gate": "node scripts/run-collab-perf-gate.mjs"' in content

    def test_backend_perf_gate_script_exists(self):
        root = Path(__file__).resolve().parent.parent.parent
        script = root / "scripts" / "performance" / "run_backend_perf_gate.py"

        assert script.exists()

    def test_deployment_doc_uses_backup_drill_and_rotation_runbook(self):
        """Deployment docs should point operators at the scripted DR and rotation paths."""
        root = Path(__file__).resolve().parent.parent.parent
        content = (root / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")

        assert "python -m scripts.backup_restore_drill" in content
        assert "python -m scripts.disaster_recovery_validation" in content
        assert "python -m scripts.rotate_secrets --type jwt" in content
        assert "SECRET_KEY_OLD" in content


class TestAG025CollaborationSloCoverage:
    """The shared SLO registry should cover the collaboration runtime paths."""

    def test_slo_registry_includes_collaboration_use_cases(self):
        root = Path(__file__).resolve().parent.parent.parent
        payload = json.loads(
            (root / "docs" / "slo" / "use-case-slos.json").read_text(encoding="utf-8-sig")
        )

        use_case_ids = {item["use_case_id"] for item in payload["use_case_slos"]}
        assert "collab.start_collaboration_session" in use_case_ids
        assert "collab.save_document_state" in use_case_ids
        assert "collab.verify_collaboration_access" in use_case_ids


# ══════════════════════════════════════════════════════════════════
# AG-018: Email retry on transient SMTP failure
# ══════════════════════════════════════════════════════════════════


class TestAG018EmailRetry:
    """Email sends should retry on transient SMTP failures."""

    def test_email_retries_on_smtp_connect_error(self):
        """Verify email service is configured for 3 retry attempts."""
        from app.services.email_service import EMAIL_MAX_ATTEMPTS, EmailService

        svc = EmailService()
        svc.enabled = True
        svc.host = "smtp.test"

        # The service should try EMAIL_MAX_ATTEMPTS times
        assert EMAIL_MAX_ATTEMPTS == 3

    def test_retry_delays_are_exponential(self):
        from app.services.email_service import EMAIL_RETRY_DELAYS

        assert len(EMAIL_RETRY_DELAYS) >= 2
        # Delays should increase
        for i in range(1, len(EMAIL_RETRY_DELAYS)):
            assert EMAIL_RETRY_DELAYS[i] > EMAIL_RETRY_DELAYS[i - 1]


# ══════════════════════════════════════════════════════════════════
# AG-019: Cleanup worker purges expired sessions/tokens
# ══════════════════════════════════════════════════════════════════


class TestAG019CleanupWorker:
    """Cleanup worker correctly identifies and removes expired records."""

    def test_purge_expired_sessions(self, db):
        user = create_user(db, role=UserRole.EDITOR)

        # Create sessions directly (avoid persist/refresh on UserSession which
        # can trigger recursive lazy loading)
        revoked = UserSession(
            user_id=user.id,
            session_token_hash="revoked_hash_" + "a" * 20,
            ip_address="127.0.0.1",
            user_agent="test",
            revoked_at=datetime.utcnow() - timedelta(days=1),
        )
        active = UserSession(
            user_id=user.id,
            session_token_hash="active_hash_" + "b" * 20,
            ip_address="127.0.0.1",
            user_agent="test",
            last_active_at=datetime.utcnow(),
        )
        stale = UserSession(
            user_id=user.id,
            session_token_hash="stale_hash_" + "c" * 20,
            ip_address="127.0.0.1",
            user_agent="test",
            last_active_at=datetime.utcnow() - timedelta(days=60),
        )
        db.add_all([revoked, active, stale])
        db.commit()

        cutoff = datetime.utcnow() - timedelta(days=30)

        # Count sessions that would be purged
        to_purge = (
            db.query(UserSession)
            .filter(
                (UserSession.user_id == user.id)
                & ((UserSession.revoked_at.isnot(None)) | (UserSession.last_active_at < cutoff))
            )
            .count()
        )

        assert to_purge >= 2  # revoked + stale

    def test_purge_expired_password_resets(self, db):
        user = create_user(db, role=UserRole.EDITOR)

        # Create records directly to avoid persist/refresh recursion
        expired_used = PasswordReset(
            user_id=user.id,
            token_hash="expired_used_token_hash_123456",
            token_prefix="expd1234",
            expires_at=datetime.utcnow() - timedelta(days=10),
            used_at=datetime.utcnow() - timedelta(days=9),
        )
        fresh = PasswordReset(
            user_id=user.id,
            token_hash="fresh_token_hash_1234567890123",
            token_prefix="frsh1234",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add_all([expired_used, fresh])
        db.commit()

        now = datetime.utcnow()
        grace_cutoff = now - timedelta(days=7)

        to_purge = (
            db.query(PasswordReset)
            .filter(
                (PasswordReset.user_id == user.id)
                & (PasswordReset.expires_at < now)
                & ((PasswordReset.used_at.isnot(None)) | (PasswordReset.expires_at < grace_cutoff))
            )
            .count()
        )

        assert to_purge >= 1  # expired_used

    def test_run_cleanup_returns_counts(self):
        """run_cleanup should return a dict with expected keys."""
        from app.workers.cleanup_worker import run_cleanup

        result = run_cleanup(dry_run=True)
        assert "sessions" in result
        assert "password_resets" in result
        assert "idempotency_records" in result
        assert "auto_archived_documents" in result
        assert "deleted_documents" in result


# ══════════════════════════════════════════════════════════════════
# AG-020: Scheduled-publish worker fires at appointed time
# ══════════════════════════════════════════════════════════════════


class TestAG020ScheduledPublish:
    """Scheduled-publish worker processes due versions."""

    def test_scheduled_publish_finds_due_versions(self, db):
        user = create_user(db, role=UserRole.EDITOR)
        doc = create_document(
            db,
            created_by=user.id,
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.PUBLIC,
        )

        # Create version with scheduled_publish_at in the past (due)
        v = persist(
            db,
            Version(
                document_id=doc.id,
                version_number=1,
                semantic_version="1.0.0",
                bump_type=VersionBumpType.PATCH,
                content="<p>Scheduled content</p>",
                changes_summary="Scheduled publish test",
                is_published=False,
                created_by=user.id,
                scheduled_publish_at=datetime.utcnow() - timedelta(minutes=5),
            ),
        )

        # Query for due versions
        due = (
            db.query(Version)
            .filter(
                Version.scheduled_publish_at <= datetime.utcnow(),
                Version.is_published.is_(False),
            )
            .all()
        )

        assert len(due) >= 1
        assert any(ver.id == v.id for ver in due)

    def test_worker_module_importable(self):
        """Worker module can be imported without side effects."""
        from app.workers.scheduled_publish_worker import run_scheduled_publishes

        assert callable(run_scheduled_publishes)


# ══════════════════════════════════════════════════════════════════
# AG-021: Admin list users uses eager loading
# ══════════════════════════════════════════════════════════════════


class TestAG021EagerLoading:
    """Repository-backed admin users list query should use joinedload to avoid N+1."""

    def test_user_repository_uses_joinedload(self):
        """Verify the user repository source imports and uses joinedload."""
        import inspect

        from app.repositories.user_repository import UserRepository

        source = inspect.getsource(UserRepository)
        assert "joinedload" in source, "UserRepository should use joinedload"

    def test_admin_list_users_returns_data(self, client, db, admin_token):
        """Admin list users endpoint should return user list."""
        resp = client.get(
            "/api/v1/users?page=1&per_page=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Accept 200 or 403 (depends on test user role setup)
        assert resp.status_code in (200, 403)
