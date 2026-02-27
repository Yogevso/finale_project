# Frontend Feature Boundaries

Feature modules should live under `src/features/<feature>/`.

Rules enforced by architecture checks:

- A feature can import:
- shared modules (`@/lib`, `@/types`, `@/config`, `@/hooks`, `@/stores`)
- its own feature internals (`@/features/<same-feature>/*`)
- another feature only through that feature's public entrypoint
  (`@/features/<other-feature>`), not deep imports.
- Shared layers (`src/components`, `src/lib`) cannot import from `src/pages`.
