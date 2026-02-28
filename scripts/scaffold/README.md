# Scaffold Generator

Task 122 introduces consistent generators/templates for baseline architecture modules.

## Supported scaffolds

- Backend:
  - `service`
  - `repository`
  - `policy`
  - `controller`
- Frontend:
  - `feature`
- Collab-server:
  - `port`
  - `adapter`

Each scaffold generates:

- implementation file,
- test stub,
- docs stub under `docs/scaffolds/`.

## Usage

```bash
node scripts/scaffold/scaffold.mjs \
  --target backend \
  --kind service \
  --name release_sync \
  --context authoring
```

Controller example:

```bash
node scripts/scaffold/scaffold.mjs \
  --target backend \
  --kind controller \
  --name users \
  --scope management
```

Dry-run plan only:

```bash
node scripts/scaffold/scaffold.mjs \
  --target frontend \
  --kind feature \
  --name release_dashboard \
  --dry-run
```

## Output checks

Validate generator output structure/tests/docs stubs:

```bash
node scripts/scaffold/check_scaffold_output.mjs
```
