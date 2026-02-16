# P4: Review and Approval - Use Case Diagram

## Actors

- `Submitter (Editor/Manager/Admin)`
- `Reviewer (Editor/Manager/Admin/System Admin)`
- `Notification Service`
- `Audit Service`

## Regular Use Cases

1. Submitter submits a draft/version for review.
2. Reviewer opens pending queue excluding own submissions.
3. Reviewer approves request and document becomes approved.
4. Reviewer rejects request and document returns to draft.
5. Submitter cancels own pending review.
6. Internal actors inspect review history timeline.

## Extreme and Edge Use Cases

1. Submit request when pending review already exists.
2. Reviewer attempts self-approval.
3. Reviewer acts on stale/non-current version.
4. Concurrent approve/reject race on same request.
5. Unauthorized reviewer attempts action outside scope.
6. Submitter attempts cancel after final decision.
7. Notification or audit emit failure after state transition.

```mermaid
flowchart LR
    SU[Submitter]
    RV[Reviewer]
    NS[Notification Service]
    AS[Audit Service]

    UC1((Submit Review Request))
    UC2((Open Pending Queue))
    UC3((Approve Review))
    UC4((Reject Review))
    UC5((Cancel Pending Review))
    UC6((View Review History))

    EX1((Block Duplicate Pending Review))
    EX2((Block Self-Approval))
    EX3((Block Stale Version Decision))
    EX4((Resolve Concurrent Decision Race))
    EX5((Handle Post-Decision Notification Failure))

    SU --> UC1
    RV --> UC2
    RV --> UC3
    RV --> UC4
    SU --> UC5
    SU --> UC6
    RV --> UC6
    NS --> EX5
    AS --> UC6

    UC3 -. include .-> UC2
    UC4 -. include .-> UC2
    UC5 -. include .-> UC1
    UC3 -. include .-> AS
    UC4 -. include .-> AS
    UC3 -. include .-> NS
    UC4 -. include .-> NS
    EX1 -. extend .-> UC1
    EX2 -. extend .-> UC3
    EX3 -. extend .-> UC3
    EX4 -. extend .-> UC3
    EX4 -. extend .-> UC4
    EX5 -. extend .-> UC3
    EX5 -. extend .-> UC4
```
