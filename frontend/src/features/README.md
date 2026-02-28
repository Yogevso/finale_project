# Frontend Feature Boundaries

Feature modules live under `src/features/<feature>/`.

## Import Rules

- A feature may import shared modules: `@/lib`, `@/types`, `@/config`, `@/hooks`, `@/stores`.
- A feature may import its own internals: `@/features/<same-feature>/*`.
- A feature may import another feature only through that feature public entrypoint: `@/features/<other-feature>`.
- Deep cross-feature imports are not allowed.

## Shared Layer Rule

Shared layers such as `src/components` and `src/lib` must not import from `src/pages`.

These rules are enforced by architecture checks in `scripts/architecture_checks/`.
