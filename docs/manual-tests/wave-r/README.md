# Wave R Manual Payload Examples

These are sanitized request body examples for manual API checks in Wave R.

Part of the Intel Documentation Platform manual-test artifacts. These payloads are commit-safe examples for ad hoc verification and support workflows.

Notes:
- Files use `.example.json` so they are safe to commit.
- Replace placeholder values (`<...>`) before use.
- Do not commit live invitation tokens.

Suggested quick use:

```powershell
curl -X POST http://localhost:8000/api/v1/auth/invitation/accept `
  -H "Content-Type: application/json" `
  -d @docs/manual-tests/wave-r/accept_invitation.example.json
```

## Related Docs

- [Root README](../../../README.md)
- [API Examples](../../API_EXAMPLES.md)
- [Development Guide](../../DEVELOPMENT.md)
