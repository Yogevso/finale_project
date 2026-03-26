# DEPENDENCY / SUPPLY-CHAIN AUDIT - 2026-03-26

## 1. Goal

Review the repository's dependency and supply-chain posture, with focus on:

- `npm audit` results for frontend and collaboration services
- Python package hygiene and auditability
- container base image hygiene
- continuous supply-chain controls in CI/CD

This is not another application-security audit. It is a dependency and build-chain
readiness audit for the current repository baseline.

---

## 2. Current Rating

- Python dependency hygiene: `6.6/10`
- Node dependency hygiene: `6.8/10`
- Container base image hygiene: `6.4/10`
- Continuous supply-chain controls: `7.1/10`

### Overall dependency/supply-chain readiness: `6.8/10`

---

## 3. Bottom Line

The repository has useful supply-chain controls already:

- a dedicated security workflow exists
- CodeQL is enabled
- dependency update automation exists through Dependabot
- repo-level audit gate scripts exist for both `pip-audit` and `npm audit`

But this is not yet a `10/10` supply-chain base.

The biggest gaps are:

1. live high-severity npm findings in direct `axios` dependencies
2. missing `collab-server` coverage in automated dependency and container scanning
3. non-reproducible Python dependency manifests
4. container and workflow references that still float on mutable tags / branches

The project is in a materially better state than the old application audit phase,
but dependency governance is still behind the codebase quality bar.

---

## 4. Findings Summary

| ID | Severity | Finding | Area |
|----|----------|---------|------|
| `SC-01` | High | Direct vulnerable `axios` ranges exist in `frontend` and `collab-server` | npm / Runtime deps |
| `SC-02` | High | Security workflow and Dependabot do not cover the `collab-server` dependency/container surface | Automation |
| `SC-03` | High | Backend Python dependency installation is not reproducibly auditable from manifests | Python deps |
| `SC-04` | Medium | `requirements.lock` is stale and does not match the declared runtime dependency set | Python deps |
| `SC-05` | Medium | Container images rely on mutable tags, including `latest`, instead of digest-pinned bases | Containers |
| `SC-06` | Medium | Security workflow still uses moving action refs like `@master` and `@main` | CI supply chain |
| `SC-07` | Low | Frontend security workflow uploads an npm audit artifact file that it never generates | CI correctness |
| `SC-08` | Low | Backend runtime manifest mixes dev/test tooling and duplicate packages into the main install set | Python deps |

---

## 5. Live Audit Results

### Node / npm

I ran live audits for the two Node applications:

- `frontend`: `npm audit --audit-level=high --json`
- `collab-server`: `npm audit --audit-level=high --json`

Results:

- `frontend`
  - total vulnerabilities: `23`
  - high: `11`
  - moderate: `8`
  - low: `4`
  - includes a direct `axios` advisory:
    - `GHSA-43fc-jf86-j433`
    - affected range reported by npm audit: `>=1.0.0 <=1.13.4`
- `collab-server`
  - total vulnerabilities: `5`
  - high: `4`
  - moderate: `1`
  - includes the same direct `axios` advisory:
    - `GHSA-43fc-jf86-j433`
    - affected range reported by npm audit: `>=1.0.0 <=1.13.4`

Important nuance:

- a meaningful part of the frontend finding count is build/test tooling
- the `axios` finding is the material runtime dependency issue because it is a
  direct application dependency in both Node services

### Python / pip

I ran two Python audit paths:

1. environment-wide:
   - `python -m pip_audit --strict --desc --format json`
2. manifest-scoped:
   - `python -m pip_audit -r requirements.txt -r requirements-dev.txt --strict --desc --format json`

What matters here is not the environment-wide CVE count. The important supply-chain
finding is that the manifest-scoped audit failed during dependency resolution, with
`pydantic-core` metadata/build preparation breaking under the current interpreter
path. That means the backend manifest is not cleanly, reproducibly auditable from
declared inputs alone in this environment.

That is a dependency governance problem even before discussing specific CVEs.

---

## 6. Detailed Findings

### `SC-01` High: Direct vulnerable `axios` ranges exist in `frontend` and `collab-server`

#### Evidence

- [package.json](C:/Users/yogev/finale_project/frontend/package.json)
- [package.json](C:/Users/yogev/finale_project/collab-server/package.json)
- live `npm audit --audit-level=high --json` runs in both directories

Specific repo evidence:

- [package.json](C:/Users/yogev/finale_project/frontend/package.json) declares `axios` at line `48` as `^1.6.5`
- [package.json](C:/Users/yogev/finale_project/collab-server/package.json) declares `axios` at line `21` as `^1.6.0`

#### What is wrong

Both Node applications currently declare `axios` ranges that fall inside the
high-severity advisory range reported by live `npm audit`.

#### Why this matters

This is not just stale dev tooling. It is a direct runtime dependency in:

- the frontend API client path
- the collaboration server's backend transport/auth path

So this is the clearest live dependency risk in the repo today.

#### What closes it

- upgrade `axios` in both Node applications to a non-affected version
- rerun `npm audit`
- add a CI gate that fails on runtime dependency findings, not only broad audit output

---

### `SC-02` High: Security workflow and Dependabot do not cover the `collab-server` dependency/container surface

#### Evidence

- [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml)
- [dependabot.yml](C:/Users/yogev/finale_project/.github/dependabot.yml)
- [npm_audit_gate.js](C:/Users/yogev/finale_project/scripts/npm_audit_gate.js)

#### What is wrong

The repo has a `collab-server`, but the main automation coverage is incomplete:

- dependency scan jobs in [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml) cover backend and frontend only
- container scanning in [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml) scans backend and frontend only
- [dependabot.yml](C:/Users/yogev/finale_project/.github/dependabot.yml) covers:
  - pip for `/backend`
  - npm for `/frontend`
  - Docker for `/backend`
  - Docker for `/frontend`
- there is no Dependabot entry for:
  - npm in `/collab-server`
  - Docker in `/collab-server`

One useful sign is that [npm_audit_gate.js](C:/Users/yogev/finale_project/scripts/npm_audit_gate.js)
already knows about both `frontend` and `collab-server`, but that repo-level intent
has not been carried into the main security workflow.

#### Why this matters

The collaboration server is part of the deployed product surface. Any automated
security story that skips it is incomplete.

#### What closes it

- add a `collab-server` dependency scan job to [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml)
- add `collab-server` to the Trivy container-scan matrix
- add npm and Docker Dependabot entries for `/collab-server`

---

### `SC-03` High: Backend Python dependency installation is not reproducibly auditable from manifests

#### Evidence

- [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt)
- live `pip-audit -r requirements.txt -r requirements-dev.txt --strict --desc --format json` failure
- [pip_audit_gate.py](C:/Users/yogev/finale_project/scripts/pip_audit_gate.py)

#### What is wrong

The backend Python dependency story is not currently reproducible enough for a
clean manifest-scoped vulnerability audit:

- the manifest-scoped `pip-audit` path failed while resolving/building metadata
- [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt) mixes pinned and ranged dependencies
- the current gate script in [pip_audit_gate.py](C:/Users/yogev/finale_project/scripts/pip_audit_gate.py)
  runs `pip-audit` against the environment rather than a locked manifest

#### Why this matters

If dependency auditing depends on "whatever happened to be installed in this
environment", then:

- audit results are harder to reproduce
- CI and local results can drift
- supply-chain review becomes less trustworthy

#### What closes it

- separate runtime and dev dependency manifests cleanly
- generate and enforce one authoritative locked Python dependency set
- make `pip-audit` run against the locked manifest, not only the environment

---

### `SC-04` Medium: `requirements.lock` is stale and does not match the declared runtime dependency set

#### Evidence

- [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt)
- [requirements.lock](C:/Users/yogev/finale_project/backend/requirements.lock)

Examples of divergence:

- `fastapi==0.115.0` in [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt) vs `fastapi==0.109.0` in [requirements.lock](C:/Users/yogev/finale_project/backend/requirements.lock)
- `python-multipart==0.0.12` in [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt) vs `python-multipart==0.0.6` in [requirements.lock](C:/Users/yogev/finale_project/backend/requirements.lock)
- `requirements.lock` also contains packages that do not look like the current
  backend runtime source of truth, such as `Flask`, `web3`, `py-solc-x`, and `pygit2`

#### What is wrong

The lockfile does not appear to be authoritative or current.

#### Why this matters

A stale lockfile is worse than no lockfile if people assume it is the audited
or deployable source of truth.

#### What closes it

- either regenerate and enforce `requirements.lock` as authoritative
- or remove/replace it with the actual lock strategy used in CI and production

---

### `SC-05` Medium: Container images rely on mutable tags, including `latest`, instead of digest-pinned bases

#### Evidence

- [Dockerfile](C:/Users/yogev/finale_project/backend/Dockerfile)
- [Dockerfile](C:/Users/yogev/finale_project/frontend/Dockerfile)
- [Dockerfile](C:/Users/yogev/finale_project/collab-server/Dockerfile)
- [docker-compose.prod.yml](C:/Users/yogev/finale_project/docker-compose.prod.yml)

Specific repo evidence:

- backend base image: `python:3.11-slim`
- frontend builder image: `node:20-alpine3.20`
- frontend runtime image: `nginxinc/nginx-unprivileged:1.27-alpine`
- collab builder/runtime image: `node:20-alpine3.20`
- prod compose uses:
  - `redis:7-alpine`
  - `ollama/ollama:latest`
  - `postgres:16-alpine`

#### What is wrong

These references are pinned to tags, not immutable digests. `latest` is the
worst case because it makes exact rebuild provenance unstable by design.

#### Why this matters

Mutable image references increase:

- rebuild drift
- patch verification ambiguity
- incident-response ambiguity when trying to answer "what exactly was deployed?"

#### What closes it

- pin all Docker base images and compose images to digests
- remove `latest` from production compose
- document the update process for digest refreshes

---

### `SC-06` Medium: Security workflow still uses moving action refs like `@master` and `@main`

#### Evidence

- [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml)

Specific repo evidence:

- `aquasecurity/trivy-action@master`
- `trufflesecurity/trufflehog@main`

#### What is wrong

These actions are pinned to moving branches instead of immutable commit SHAs.

#### Why this matters

GitHub Actions are part of the supply chain. Mutable action refs increase the
chance of unintended behavior changes or upstream compromise affecting the repo.

#### What closes it

- pin security-sensitive GitHub Actions to immutable SHAs
- maintain a documented refresh cadence for action updates

---

### `SC-07` Low: Frontend security workflow uploads an npm audit artifact file that it never generates

#### Evidence

- [security.yml](C:/Users/yogev/finale_project/.github/workflows/security.yml)

#### What is wrong

The frontend dependency scan runs:

- `npm audit --audit-level=high`

But the later artifact upload step points at:

- `frontend/npm-audit-report.json`

No earlier step creates that file.

#### Why this matters

This does not create a vulnerability by itself, but it does make the security
workflow less trustworthy and less useful for investigation.

#### What closes it

- either generate JSON output explicitly and upload it
- or remove the broken artifact path

---

### `SC-08` Low: Backend runtime manifest mixes dev/test tooling and duplicate packages into the main install set

#### Evidence

- [requirements.txt](C:/Users/yogev/finale_project/backend/requirements.txt)

Specific repo evidence:

- duplicate `Pillow` declarations at lines `40` and `61`
- main runtime manifest includes:
  - `pytest`
  - `pytest-asyncio`
  - `pytest-cov`
  - `pytest-xdist`
  - `ruff`
  - `mypy`

#### What is wrong

The runtime install surface is broader and noisier than it needs to be.

#### Why this matters

This increases:

- attack surface in environments that install directly from `requirements.txt`
- audit noise
- reproducibility drift between local, CI, and production

#### What closes it

- move test/lint/type-check tooling fully out of the runtime dependency file
- deduplicate overlapping packages
- keep runtime manifests minimal

---

## 7. Recommended Execution Order

1. `SC-01` upgrade `axios` in both Node applications and rerun `npm audit`
2. `SC-02` add `collab-server` to security workflow, container scan, and Dependabot
3. `SC-03` / `SC-04` establish one authoritative Python lock/audit path
4. `SC-05` / `SC-06` pin container images and GitHub Actions to immutable references
5. `SC-07` / `SC-08` clean up the broken frontend audit artifact path and Python manifest hygiene

---

## 8. Final Verdict

The codebase itself is now in excellent shape, but dependency and build-chain
governance are still behind that standard.

This repo is **good enough to operate**, but it is **not yet a 10/10 dependency /
supply-chain base**.

The shortest path to materially improving that rating is:

- remove the live direct `axios` findings
- stop skipping the `collab-server` in automated security coverage
- make Python dependency auditing reproducible from authoritative manifests
