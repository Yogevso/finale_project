# P0: Access and Identity - Use Case Diagram

## Actors

- `System Admin`
- `Admin`
- `Manager`
- `Invitee`
- `Authenticated User`
- `Security Operations`

## Regular Use Cases

1. Inviter creates invitation for target role.
2. Inviter lists and tracks invitation status.
3. Invitee validates invitation token from public link.
4. Invitee accepts invitation and creates account.
5. User logs in and receives access/refresh tokens.
6. User refreshes access token with valid refresh token.
7. User reads own profile and changes password.
8. User logs out and invalidates active refresh sessions.

## Extreme and Edge Use Cases

1. Expired, cancelled, or already-accepted invitation token is used.
2. Inviter attempts role escalation outside role hierarchy.
3. Username/email collision occurs during invitation acceptance.
4. Brute-force login attempts trigger security controls.
5. Replay attack attempts reuse consumed refresh token.
6. Suspicious session pattern triggers forced logout.
7. Password change attempts with incorrect current password.
8. Cross-tenant invitation visibility attempt is blocked.

```mermaid
flowchart LR
    SA[System Admin]
    AD[Admin]
    MG[Manager]
    IV[Invitee]
    AU[Authenticated User]
    SOC[Security Operations]

    UC1((Create Invitation))
    UC2((List Invitations))
    UC3((Validate Invitation Token))
    UC4((Accept Invitation))
    UC5((Login))
    UC6((Refresh Access Token))
    UC7((Change Password))
    UC8((Logout))

    EX1((Handle Expired or Invalid Token))
    EX2((Block Role Escalation))
    EX3((Block Credential Stuffing))
    EX4((Detect Refresh Replay))
    EX5((Force Session Revocation))

    SA --> UC1
    AD --> UC1
    MG --> UC1
    SA --> UC2
    AD --> UC2
    MG --> UC2
    IV --> UC3
    IV --> UC4
    AU --> UC5
    AU --> UC6
    AU --> UC7
    AU --> UC8
    SOC --> EX5

    UC4 -. include .-> UC3
    UC5 -. include .-> UC6
    UC8 -. include .-> EX5
    EX1 -. extend .-> UC3
    EX2 -. extend .-> UC1
    EX3 -. extend .-> UC5
    EX4 -. extend .-> UC6
```
