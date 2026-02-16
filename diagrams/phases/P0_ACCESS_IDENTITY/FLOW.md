# P0: Access and Identity - Flow Diagram

```mermaid
flowchart TD
    A[Inviter chooses role and tenant/company] --> B{Actor has hierarchy permission?}
    B -- No --> B1[Reject request 403]
    B -- Yes --> C{Duplicate user or pending invite exists?}
    C -- Yes --> C1[Reject request 400]
    C -- No --> D[Create invitation token + expiry + audit]
    D --> E[Invitee opens validation endpoint]
    E --> F{Invitation token pending and not expired?}
    F -- No --> F1[Return invalid token state]
    F -- Yes --> G[Invitee submits registration payload]
    G --> H{Username/email unique?}
    H -- No --> H1[Reject request 400]
    H -- Yes --> I[Hash password and create user]
    I --> J[Mark invitation accepted]
    J --> K[Issue access + refresh tokens]
    K --> L[Session established]

    L --> M[User login attempts]
    M --> N{Credentials valid and account active?}
    N -- No --> N1[Return 401 or 403]
    N -- Yes --> O[Create session token records]
    O --> P[User accesses /auth/me and protected APIs]
    P --> Q[Client calls refresh before access expiry]
    Q --> R{Refresh token hash valid and unexpired?}
    R -- No --> R1[Reject refresh and require login]
    R -- Yes --> S[Issue new access token]
    S --> T[Optional password change]
    T --> U{Old password matches hash?}
    U -- No --> U1[Reject change 400]
    U -- Yes --> V[Persist new hash]
    V --> W[Logout marks refresh tokens used]
```
