# Context Map Artifacts

This directory captures upstream/downstream dependencies across major bounded contexts.

Part of the Intel Documentation Platform documentation set. Use these artifacts when a change affects ownership boundaries, context flow, or integration direction.

## Primary Context Map

```mermaid
flowchart LR
  AI[Access and Identity]
  GV[Governance and Tenant Setup]
  AU[Authoring and Assembly]
  RV[Review and Approval]
  CL[Collaboration]
  DS[Distribution and Consumption]
  FA[Feedback Analytics and Audit]

  AI --> AU
  AI --> RV
  AI --> CL
  AI --> DS
  AI --> FA
  GV --> AU
  GV --> DS
  AU --> RV
  AU --> CL
  AU --> DS
  RV --> DS
  DS --> FA
  AU --> FA
  CL --> FA
```

## Artifacts

- [contexts.md](./contexts.md): dependency catalog and integration expectations.

## Update Rule

Update this directory when a change:

- introduces a new upstream/downstream dependency
- changes ownership boundaries
- changes contract flow between backend/frontend/collab contexts

## Related Docs

- [Root README](../../README.md)
- [Architecture](../ARCHITECTURE.md)
- [ADRs](../adr/README.md)
