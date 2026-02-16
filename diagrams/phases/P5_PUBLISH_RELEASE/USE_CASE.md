# P5: Publish and Release - Use Case Diagram

## Actors

- `Publisher (Manager/Admin/System Admin)`
- `Editor`
- `Notification Service`
- `Audit Service`

## Regular Use Cases

1. Publisher inspects release candidate versions.
2. Publisher publishes approved version.
3. System marks version as published and document as active.
4. Notification pipeline emits publish events.
5. Editor/internal users consume published immutable state.

## Extreme and Edge Use Cases

1. Publish attempt without approved review.
2. Publish attempt on already-published version.
3. Concurrent duplicate publish requests race.
4. Editor attempts mutation on published version.
5. Post-publish notification delivery failure.
6. Release needs rollback after publication.
7. Publish actor lacks role despite valid auth session.

```mermaid
flowchart LR
    PB[Publisher]
    ED[Editor]
    NS[Notification Service]
    AS[Audit Service]

    UC1((Inspect Release Candidates))
    UC2((Publish Version))
    UC3((Activate Document))
    UC4((Emit Publish Notifications))
    UC5((Enforce Published Immutability))

    EX1((Reject Publish Without Approved Review))
    EX2((Reject Duplicate Publish))
    EX3((Resolve Publish Race Condition))
    EX4((Reject Mutation on Published Version))
    EX5((Handle Notification Delivery Failure))
    EX6((Execute Rollback or Hotfix Path))

    PB --> UC1
    PB --> UC2
    PB --> UC3
    NS --> UC4
    ED --> UC5
    AS --> UC2

    UC2 -. include .-> UC1
    UC2 -. include .-> UC3
    UC2 -. include .-> UC4
    UC3 -. include .-> UC5
    EX1 -. extend .-> UC2
    EX2 -. extend .-> UC2
    EX3 -. extend .-> UC2
    EX4 -. extend .-> UC5
    EX5 -. extend .-> UC4
    EX6 -. extend .-> UC3
```
