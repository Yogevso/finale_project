# ADR-0005: Error Boundary Policy

## Status

Accepted

## Context

The backend had three competing patterns for expected failures:

- `DomainError` subclasses in some service and domain flows
- direct `fastapi.HTTPException` raises leaking out of service/application code
- typed `Result[...]` return values in a few CQRS handlers

That mix made failure handling inconsistent, forced command handlers to translate both
`DomainError` and `HTTPException`, and blurred the boundary between application code and
transport code.

## Decision

The backend uses one primary expected-failure contract:

- `DomainError` subclasses are the only expected error style in domain, application,
  collaboration, and service layers.
- `HTTPException` is restricted to transport boundaries:
  routes, dependency guards, middleware, and websocket adapters.
- `Result[...]` is restricted to command/query boundary adapters that intentionally expose
  typed success/error unions to callers.

Transport-specific response details that must survive mapping, such as
`WWW-Authenticate` or `X-Error-Code`, are carried on `DomainError.headers`.

## Consequences

- Services and context APIs stay framework-agnostic.
- FastAPI response behavior remains stable through the central `DomainError` handler.
- Command/query handlers no longer need to translate `HTTPException`.
- Architecture fitness checks can reject new boundary drift automatically.
