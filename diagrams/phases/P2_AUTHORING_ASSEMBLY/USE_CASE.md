# P2: Authoring and Content Assembly - Use Case Diagram

## Actors

- `Editor`
- `Manager`
- `Admin`
- `Authenticated User`

## Regular Use Cases

1. Editor creates document with initial placeholder version.
2. Internal user lists/reads documents in authorized scope.
3. Editor updates documents; service creates patch versions when fields change.
4. Editor/manager/admin creates and updates versions under review-state rules.
5. Editor/manager/admin uploads attachments and generated artifacts.
6. Authenticated users create and maintain comment threads.
7. Permissioned manager/admin assigns companies to documents.

## Extreme and Edge Use Cases

1. New version request while pending review exists.
2. Attempt to update published or review-locked version.
3. Publish request without approved review.
4. Unsupported or oversized attachment upload.
5. Non-admin attempts attachment deletion.
6. Unauthorized comment content edit/resolve/delete operation.
7. Cross-tenant visibility risk on endpoints missing explicit scope checks.

```mermaid
flowchart LR
    ED[Editor]
    MG[Manager]
    AD[Admin]
    AU[Authenticated User]

    UC1((Create Document))
    UC2((List And Read Documents))
    UC3((Update Document Metadata))
    UC4((Manage Versions))
    UC5((Manage Attachments And Artifacts))
    UC6((Manage Comments))
    UC7((Assign Companies))

    EX1((Block Version Create During Pending Review))
    EX2((Block Update Of Locked Version))
    EX3((Block Publish Without Approved Review))
    EX4((Reject Invalid Upload))
    EX5((Block Attachment Delete For Non Admin))
    EX6((Block Unauthorized Comment Mutation))
    EX7((Detect Missing Tenant Scope Checks))

    ED --> UC1
    ED --> UC2
    ED --> UC3
    ED --> UC4
    ED --> UC5
    MG --> UC4
    AD --> UC4
    AU --> UC6
    MG --> UC7
    AD --> UC7

    UC4 -. include .-> UC3
    UC5 -. include .-> UC2

    EX1 -. extend .-> UC4
    EX2 -. extend .-> UC4
    EX3 -. extend .-> UC4
    EX4 -. extend .-> UC5
    EX5 -. extend .-> UC5
    EX6 -. extend .-> UC6
    EX7 -. extend .-> UC2
    EX7 -. extend .-> UC4
    EX7 -. extend .-> UC5
    EX7 -. extend .-> UC6
```
