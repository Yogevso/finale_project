# P0: Access and Identity - Use Case Diagram

## Actors

- `System Admin`
- `Admin`
- `Manager`
- `Invitee`
- `Authenticated User`

## Regular Use Cases

1. Admin/manager creates and manages invitations.
2. Invitee validates invitation token.
3. Invitee accepts invitation and provisions account.
4. Public user self-registers with unique email/username.
5. User logs in and receives access and refresh tokens.
6. User refreshes access token with a valid refresh token.
7. User reads profile and changes password.
8. User logs out and invalidates stored refresh sessions.

## Extreme and Edge Use Cases

1. Expired, cancelled, or used invitation token is submitted.
2. Invitation acceptance fails due to existing email or username.
3. Inviter attempts role escalation outside hierarchy bounds.
4. Non-system actor attempts out-of-scope invitation operation.
5. Repeated failed login attempts trigger rate limiting.
6. Refresh token is invalid, expired, or already invalidated.
7. Inactive account attempts login.
8. Forgot-password endpoint receives abusive request volume.

```mermaid
flowchart LR
    SA[System Admin]
    AD[Admin]
    MG[Manager]
    IV[Invitee]
    AU[Authenticated User]

    UC1((Manage Invitations))
    UC2((Validate Invitation Token))
    UC3((Accept Invitation))
    UC4((Self Register Account))
    UC5((Login))
    UC6((Refresh Access Token))
    UC7((Read Profile and Change Password))
    UC8((Logout))

    EX1((Reject Invalid Invitation Token))
    EX2((Reject Duplicate Identity Claims))
    EX3((Block Role Escalation Invite))
    EX4((Block Out Of Scope Invite Access))
    EX5((Throttle Repeated Login Failures))
    EX6((Reject Invalid Refresh Token))
    EX7((Block Inactive User Login))
    EX8((Throttle Forgot Password Abuse))

    SA --> UC1
    AD --> UC1
    MG --> UC1
    IV --> UC2
    IV --> UC3
    IV --> UC4
    AU --> UC5
    AU --> UC6
    AU --> UC7
    AU --> UC8

    UC3 -. include .-> UC2
    UC8 -. include .-> UC6

    EX1 -. extend .-> UC2
    EX2 -. extend .-> UC3
    EX3 -. extend .-> UC1
    EX4 -. extend .-> UC1
    EX5 -. extend .-> UC5
    EX6 -. extend .-> UC6
    EX7 -. extend .-> UC5
    EX8 -. extend .-> UC5
```
