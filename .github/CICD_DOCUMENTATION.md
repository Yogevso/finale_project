# CI/CD Pipeline Documentation

This document describes the GitHub Actions CI/CD pipeline for the Document Portal V2 project.

## 📁 Workflow Files

| File | Purpose | Trigger |
|------|---------|---------|
| [ci.yml](workflows/ci.yml) | Tests, linting, type checking | Push/PR to main, develop |
| [cd.yml](workflows/cd.yml) | Build and deploy Docker images | Push to main, tags, manual |
| [security.yml](workflows/security.yml) | Security scanning | Push/PR, daily schedule |
| [pr-checks.yml](workflows/pr-checks.yml) | PR automation and review | Pull requests |

---

## 🔄 CI Workflow (`ci.yml`)

Runs on every push and pull request to ensure code quality.

### Jobs

```
┌─────────────────┐    ┌─────────────────┐
│  backend-lint   │    │  frontend-lint  │
│  (Ruff, MyPy)   │    │  (ESLint, TSC)  │
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│  backend-tests  │    │  frontend-build │
│   (pytest)      │    │   (Vite)        │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌─────────────────┐
         │   frontend-e2e  │
         │  (Playwright)   │
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │   ci-success    │
         │   (Summary)     │
         └─────────────────┘
```

### Test Coverage
- **Backend**: 262+ pytest tests with coverage reporting
- **Frontend**: 278 Playwright E2E tests across 13 spec files

### Artifacts
- `backend-test-results` - JUnit XML test results
- `playwright-report` - HTML test report
- `e2e-test-results` - Playwright traces

---

## 🚀 CD Workflow (`cd.yml`)

Builds Docker images and deploys to environments.

### Jobs

```
┌─────────────────┐
│      test       │ (reuses ci.yml)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│backend │ │frontend│
│ build  │ │ build  │
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         ▼
┌─────────────────┐
│ deploy-staging  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│deploy-production│ (manual approval)
└─────────────────┘
```

### Docker Images
- Published to: `ghcr.io/yogevso/finale_project/backend`
- Published to: `ghcr.io/yogevso/finale_project/frontend`

### Tags
- `latest` - Latest from main branch
- `sha-xxxxxx` - Commit SHA
- `v1.0.0` - Semantic version tags

### Environments
| Environment | URL | Approval |
|-------------|-----|----------|
| staging | staging.portal.example.com | Automatic |
| production | portal.example.com | Manual |

---

## 🔒 Security Workflow (`security.yml`)

Comprehensive security scanning.

### Scans

| Scan | Tool | Purpose |
|------|------|---------|
| Python deps | Safety, pip-audit | Vulnerability detection |
| Node deps | npm audit | Vulnerability detection |
| SAST | CodeQL | Static code analysis |
| Containers | Trivy | Image vulnerabilities |
| Secrets | Gitleaks, TruffleHog | Secret detection |
| Licenses | pip-licenses, license-checker | Compliance |

### Schedule
- Runs daily at 2 AM UTC
- Also runs on pushes and PRs

---

## 📋 PR Checks Workflow (`pr-checks.yml`)

Automates pull request management.

### Features
- **Auto-labeling**: Labels PRs based on changed files
- **Size check**: Warns on large PRs (>1000 lines)
- **Title check**: Enforces conventional commit format
- **Dependency review**: Checks for vulnerable dependencies
- **Auto-merge**: Merges Dependabot minor/patch updates

---

## ⚙️ Configuration Files

| File | Purpose |
|------|---------|
| [labeler.yml](labeler.yml) | PR auto-labeling rules |
| [commitlint.config.js](commitlint.config.js) | Commit message format |
| [dependabot.yml](dependabot.yml) | Dependency update settings |
| [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) | PR template |
| [ISSUE_TEMPLATE/](ISSUE_TEMPLATE/) | Issue templates |

---

## 🔐 Required Secrets

Configure these in **Settings > Secrets and variables > Actions**:

### Required
| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Auto-provided by GitHub |

### Optional (for deployment)
| Secret | Description |
|--------|-------------|
| `STAGING_HOST` | Staging server hostname |
| `STAGING_USER` | Staging SSH username |
| `STAGING_SSH_KEY` | Staging SSH private key |
| `PRODUCTION_HOST` | Production server hostname |
| `PRODUCTION_USER` | Production SSH username |
| `PRODUCTION_SSH_KEY` | Production SSH private key |
| `GITLEAKS_LICENSE` | Gitleaks enterprise license (optional) |

---

## 📊 Environment Variables

Configure in **Settings > Environments**:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Backend API URL for frontend | `https://api.portal.example.com` |

---

## 🏷️ Conventional Commits

All commits should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Code style (formatting) |
| `refactor` | Code refactoring |
| `perf` | Performance improvement |
| `test` | Tests |
| `build` | Build system |
| `ci` | CI/CD |
| `chore` | Maintenance |
| `revert` | Revert commit |

### Examples
```bash
feat(auth): add OAuth2 login support
fix(upload): handle files larger than 10MB
docs(readme): update installation instructions
ci(github): add security scanning workflow
```

---

## 🚦 Branch Protection

Recommended settings for the `main` branch:

1. ✅ Require pull request reviews before merging
2. ✅ Require status checks to pass before merging
   - `CI Success` (from ci.yml)
   - `PR Summary` (from pr-checks.yml)
3. ✅ Require branches to be up to date before merging
4. ✅ Include administrators
5. ✅ Restrict who can push to matching branches

---

## 🔧 Manual Workflows

### Trigger CD Manually
1. Go to **Actions > CD - Build & Deploy**
2. Click **Run workflow**
3. Select environment (staging/production)
4. Optionally skip tests

### Create a Release
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

This will:
1. Run all tests
2. Build and push Docker images tagged with the version
3. Deploy to staging
4. Create a GitHub Release (after production deployment)

---

## 📈 Monitoring

### GitHub Actions Dashboard
- View workflow runs: **Actions** tab
- View workflow logs: Click on any run
- Re-run failed jobs: **Re-run failed jobs** button

### Artifacts
Artifacts are retained for:
- Test results: 30 days
- Build artifacts: 7 days
- Security reports: 30 days
- License reports: 90 days
