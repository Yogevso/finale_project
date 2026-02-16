# P2: Authoring and Content Assembly - Use Case Diagram

## Actors

- `Editor`
- `Manager`
- `Admin`
- `Internal Collaborator`
- `Storage Service`

## Regular Use Cases

1. Editor creates draft document and initial version.
2. Editor updates metadata and structured content.
3. Editor creates additional draft versions.
4. Editor uploads attachments and generated artifacts.
5. Internal collaborator creates and updates comments.
6. Admin/editor resolves threads.
7. Manager/admin assigns companies to company-visible documents.

## Extreme and Edge Use Cases

1. New version request when pending review already exists.
2. Attempt to edit immutable or workflow-locked version.
3. Oversized or unsupported attachment upload.
4. Attachment processing/storage failure during upload.
5. Unauthorized comment edit/resolve attempt.
6. Invalid or unauthorized company assignment set.
7. Content payload schema mismatch causing partial updates.

```mermaid
flowchart LR
    ED[Editor]
    MG[Manager]
    AD[Admin]
    IC[Internal Collaborator]
    ST[Storage Service]

    UC1((Create Document Draft))
    UC2((Update Draft Metadata and Content))
    UC3((Create Draft Version))
    UC4((Upload Attachment))
    UC5((Generate Word Artifact))
    UC6((Create or Edit Comment))
    UC7((Resolve Comment Thread))
    UC8((Assign Companies))

    EX1((Block Version Creation During Pending Review))
    EX2((Block Immutable Version Edit))
    EX3((Reject Invalid File Upload))
    EX4((Handle Storage Failure))
    EX5((Reject Unauthorized Comment Mutation))
    EX6((Reject Invalid Company Assignment))

    ED --> UC1
    ED --> UC2
    ED --> UC3
    ED --> UC4
    ED --> UC5
    IC --> UC6
    ED --> UC6
    AD --> UC7
    ED --> UC7
    MG --> UC8
    AD --> UC8
    ST --> UC4
    ST --> UC5

    UC5 -. include .-> UC4
    UC7 -. include .-> UC6
    EX1 -. extend .-> UC3
    EX2 -. extend .-> UC2
    EX2 -. extend .-> UC3
    EX3 -. extend .-> UC4
    EX4 -. extend .-> UC4
    EX5 -. extend .-> UC6
    EX6 -. extend .-> UC8
```
