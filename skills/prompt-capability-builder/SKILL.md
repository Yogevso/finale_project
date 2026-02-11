---
name: prompt-capability-builder
description: Convert each user prompt into a concrete, reusable capability definition for software delivery with clear trigger, inputs, outputs, constraints, implementation workflow, and acceptance checks. Use when a user asks to create or update a capability/skill from a prompt, when prompt requests are ambiguous and need standardization, or when work must be delegated with consistent execution quality across backend, frontend, devops, or full-stack work.
---

# Prompt Capability Builder

## Overview

Transform any prompt into a specific capability that can be implemented, tested, and reused in a software project.
Produce explicit contracts and acceptance checks so execution is consistent across turns and agents.

## Workflow

1. Parse the prompt into objective and boundaries.
- Extract goal, actor, domain objects, constraints, and non-goals.
- Mark missing critical data (inputs, environment, target output).

2. Classify the capability.
- Pick one primary type: `transformation`, `retrieval`, `generation`, `orchestration`, `validation`, or `integration`.
- Pick one domain: `backend`, `frontend`, `devops`, or `full-stack`.
- Split combined requests into a primary capability plus secondary support capabilities.

3. Write a concrete capability spec.
- Fill all required sections:
  - `Capability Name`
  - `Domain`
  - `Purpose`
  - `Trigger Conditions`
  - `Required Inputs`
  - `Optional Inputs`
  - `Repo Context`
  - `Output Contract`
  - `Execution Steps`
  - `Deliverables`
  - `Tools/Dependencies`
  - `Constraints/Safety`
  - `Failure Modes`
  - `Acceptance Tests`

4. Set implementation freedom intentionally.
- Use high freedom (text guidance) for adaptive tasks with many valid methods.
- Use medium freedom (structured pseudocode/scripts with parameters) for repeatable tasks with moderate variance.
- Use low freedom (deterministic script/sequence) for fragile or high-risk tasks.

5. Return the capability in the requested delivery mode.
- Generate or update a skill when the user asks for a reusable capability.
- Return a compact execution-ready spec for one-off tasks.
- Ask up to 3 targeted questions only when required inputs are missing.

## Domain Rules

Apply these rules based on the selected domain:

- `backend`
- Include API contract impact, auth/permissions impact, and data/storage impact.
- Include validation of error paths and role/access behavior.

- `frontend`
- Include UX state flows (loading, empty, error, success).
- Include accessibility and responsive behavior checks.

- `devops`
- Include runtime topology, environment variables, and health checks.
- Include rollback/safe recovery strategy.

- `full-stack`
- Split capability into backend + frontend + integration checkpoints.
- Define handoff contracts between layers.

## Output Template

Use this exact structure unless the user requests a different format:

```markdown
Capability Name: <hyphen-case-when-reusable>
Domain: <backend|frontend|devops|full-stack>
Purpose: <one sentence>
Trigger Conditions:
- ...
Required Inputs:
- ...
Optional Inputs:
- ...
Repo Context:
- Relevant paths:
- Existing constraints:
Output Contract:
- Format:
- Fields:
- Quality Criteria:
Execution Steps:
1. ...
2. ...
3. ...
Deliverables:
- Files to create/update:
- Commands to run:
- Evidence to report:
Tools/Dependencies:
- ...
Constraints/Safety:
- ...
Failure Modes:
- ...
Acceptance Tests:
1. Given ... When ... Then ...
2. Given ... When ... Then ...
3. Given ... When ... Then ...
```

## Quality Gate

Enforce these checks before returning output:
- Map each execution step to at least one required input and one output field.
- Include at least one happy-path and two failure-path acceptance tests.
- Keep requirements measurable; avoid vague phrases such as "handle properly".
- Remove placeholder text (`TODO`, `<fill>`, `TBD`).
- Require domain checks: API/permissions for backend, accessibility/responsiveness for frontend, health/rollback for devops.
- Ensure deliverables list concrete file paths or command categories.

## References

Read `references/capability-patterns.md` when classification is unclear or when quality criteria are weak.
Read `references/project-domain-playbook.md` when generating domain-specific acceptance checks and deliverables.
