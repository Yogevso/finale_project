# Scaffold Generator

Task 122 generator for consistent architecture scaffolding.

## Supported Targets

- Backend: `service`, `repository`, `policy`, `controller`
- Frontend: `feature`
- Collab-server: `port`, `adapter`

Generated output includes:

- implementation file
- test stub
- docs stub under `docs/scaffolds/`

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

Dry-run only:

```bash
node scripts/scaffold/scaffold.mjs \
  --target frontend \
  --kind feature \
  --name release_dashboard \
  --dry-run
```

## Validate Output

```bash
node scripts/scaffold/check_scaffold_output.mjs
```
