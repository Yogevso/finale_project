# P3: Real-Time Collaboration - Use Case Diagram

## Actors

- `Editor`
- `Viewer`
- `Customer`
- `Collaboration Server`
- `Session Monitor`

## Regular Use Cases

1. Collaborator requests document-scoped collaboration token.
2. Collaborator connects to document WebSocket channel.
3. Collaboration server hydrates document state.
4. Collaborator starts tracked collaboration session.
5. Collaborator edits/presence-updates in real-time.
6. Collaboration server persists debounced CRDT state.
7. User or service creates snapshot (manual or auto).
8. Collaborator ends session and activity is logged.

## Extreme and Edge Use Cases

1. Token is stale, invalid, or for wrong document id.
2. Read-only collaborator attempts write operation.
3. Network partition causes delayed state flush/retry burst.
4. Mid-session permission change revokes write access.
5. Snapshot flood attempts exceed policy limits.
6. Zombie sessions remain active after disconnect.
7. Activity spam degrades analytics or storage.

```mermaid
flowchart LR
    ED[Editor]
    VW[Viewer]
    CU[Customer]
    CS[Collaboration Server]
    SM[Session Monitor]

    UC1((Request Collaboration Token))
    UC2((Connect WebSocket))
    UC3((Load Collaboration State))
    UC4((Start Session))
    UC5((Realtime Edit and Presence))
    UC6((Persist CRDT State))
    UC7((Create Snapshot))
    UC8((End Session))

    EX1((Reject Invalid Token or Doc Mismatch))
    EX2((Enforce Read-Only Mode))
    EX3((Handle State Persist Backpressure))
    EX4((Downgrade Write Permission Mid-Session))
    EX5((Throttle Snapshot Frequency))
    EX6((Cleanup Zombie Sessions))

    ED --> UC1
    VW --> UC1
    CU --> UC1
    ED --> UC2
    VW --> UC2
    CU --> UC2
    CS --> UC3
    ED --> UC4
    VW --> UC4
    CU --> UC4
    ED --> UC5
    VW --> UC5
    CU --> UC5
    CS --> UC6
    ED --> UC7
    CS --> UC7
    ED --> UC8
    VW --> UC8
    CU --> UC8
    SM --> EX6

    UC2 -. include .-> UC3
    UC5 -. include .-> UC6
    UC8 -. include .-> UC4
    EX1 -. extend .-> UC2
    EX2 -. extend .-> UC5
    EX3 -. extend .-> UC6
    EX4 -. extend .-> UC5
    EX5 -. extend .-> UC7
    EX6 -. extend .-> UC8
```
