# Capability Patterns

## Quick Classification

Use this map to pick the primary capability type:

| Type | Use When | Typical Output |
|---|---|---|
| `transformation` | Input data must become a different structure | Converted file/data with schema compliance |
| `retrieval` | User needs facts or records without heavy modification | Ranked results with source attribution |
| `generation` | User needs new content/artifacts from instructions | Draft, document, UI/code artifact |
| `orchestration` | Multiple tools/steps must run in sequence | Workflow run with checkpoints |
| `validation` | Existing output must be checked against rules | Pass/fail report with violations |
| `integration` | Systems/services must exchange data or actions | Connected flow with contract mapping |

## Prompt Decomposition Checklist

Extract and write explicitly:
- `Goal`: What must be true when done.
- `Actor`: Who/what executes the capability.
- `Objects`: Main entities/files/endpoints involved.
- `Constraints`: Time, cost, security, environment, format.
- `Evidence`: How success will be proven.

If any item is missing, either infer conservatively or ask targeted questions.

## Strong vs Weak Specs

Prefer strong wording:
- Strong: `Return JSON with fields id:string, status:enum[ok,failed], latency_ms:number`
- Weak: `Return structured data`

- Strong: `Fail if coverage drops below 85%`
- Weak: `Keep good test quality`

- Strong: `Retry API call up to 3 times with exponential backoff`
- Weak: `Handle API failures`

## Minimal Acceptance Test Set

Always include:
1. Happy path test with representative input.
2. Invalid input test (schema/type/range failure).
3. External failure test (timeout/dependency unavailable/permission denied).
