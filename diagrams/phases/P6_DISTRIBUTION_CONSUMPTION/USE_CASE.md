# P6: Distribution and Consumption - Use Case Diagram

## Actors

- `Public User`
- `Customer`
- `Internal Viewer`
- `Access Control Service`
- `Delivery Layer (API/CDN)`

## Regular Use Cases

1. Public user browses active public documents.
2. Public user opens details and performs public search.
3. Customer accesses portal-scoped document catalog.
4. Customer opens document and downloads authorized attachment.
5. Internal viewer uses internal read-only endpoints.
6. Delivery layer serves content and metadata efficiently.

## Extreme and Edge Use Cases

1. Unauthorized customer attempts access to non-assigned document.
2. Direct attachment URL guessing/enumeration attempt.
3. Cross-tenant data exposure attempt via filters.
4. Traffic spike causes latency or cache stampede.
5. Stale permission cache allows temporary over-access.
6. Active document has missing published artifact.
7. Search query abuse or scraping behavior.

```mermaid
flowchart LR
    PU[Public User]
    CU[Customer]
    IV[Internal Viewer]
    ACL[Access Control Service]
    DL[Delivery Layer]

    UC1((Browse Public Catalog))
    UC2((View Public Document and Search))
    UC3((Browse Portal Catalog))
    UC4((View Portal Document))
    UC5((Download Attachment))
    UC6((Browse Internal Viewer Endpoints))

    EX1((Reject Unauthorized Document Access))
    EX2((Block Attachment Enumeration))
    EX3((Prevent Cross-Tenant Leakage))
    EX4((Mitigate Traffic Spike))
    EX5((Recover Missing Published Artifact))

    PU --> UC1
    PU --> UC2
    CU --> UC3
    CU --> UC4
    CU --> UC5
    IV --> UC6
    ACL --> EX1
    ACL --> EX3
    DL --> EX4

    UC4 -. include .-> UC3
    UC5 -. include .-> UC4
    UC5 -. include .-> ACL
    EX1 -. extend .-> UC4
    EX1 -. extend .-> UC5
    EX2 -. extend .-> UC5
    EX3 -. extend .-> UC3
    EX3 -. extend .-> UC6
    EX4 -. extend .-> UC1
    EX4 -. extend .-> UC3
    EX5 -. extend .-> UC2
```
