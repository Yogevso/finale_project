# P2: Authoring and Content Assembly - Flow Diagram

```mermaid
flowchart TD
    A[Editor starts authoring] --> B{Editor role and tenant scope valid?}
    B -- No --> B1[Reject 403]
    B -- Yes --> C[Create document shell + initial draft version]
    C --> D[Update metadata, visibility, and structured content]
    D --> E{Pending review already exists?}
    E -- Yes --> E1[Block new version 409]
    E -- No --> F[Create additional draft version]
    F --> G{Version is published or in review terminal lock?}
    G -- Yes --> G1[Block edits 400 or 409]
    G -- No --> H[Persist version patch]

    H --> I[Upload attachments]
    I --> J{File type and size pass service rules?}
    J -- No --> J1[Reject upload 400]
    J -- Yes --> K[Persist blob and attachment metadata]
    K --> L[Optional generated Word artifact]

    L --> M[Collaborators create comments/replies]
    M --> N{Author or privileged actor editing/resolving?}
    N -- No --> N1[Reject comment update 403]
    N -- Yes --> O[Persist comment mutation and resolution flags]

    O --> P[Manager/Admin assigns document to companies]
    P --> Q{assign_companies permission granted?}
    Q -- No --> Q1[Reject assignment 403]
    Q -- Yes --> R[Persist company linkage and access scope]
```
