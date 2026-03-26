# Context Dependencies

| Context | Upstream Contexts | Downstream Contexts | Integration Type |
| --- | --- | --- | --- |
| Access and Identity | None | All contexts | Auth token, role/permission decisions |
| Governance and Tenant Setup | Access and Identity | Authoring, Distribution | Tenant scoping, system settings |
| Authoring and Assembly | Access and Identity, Governance | Review, Collaboration, Distribution, Analytics | CRUD and version workflows |
| Review and Approval | Access and Identity, Authoring | Distribution, Analytics | Approval state transitions |
| Collaboration | Access and Identity, Authoring | Analytics | Realtime sessions and snapshots |
| Distribution and Consumption | Access and Identity, Governance, Authoring, Review | Analytics | Portal/viewer reads and download flows |
| Feedback Analytics and Audit | All operational contexts | None | Event ingestion, metrics, audit visibility |

## Notes

- Cross-context writes should go through owner service contracts only.
- Route and websocket entrypoints should call owner context APIs in `app.application.contexts.*.api`, not `app.web.controllers.*`.
- For architecture-level dependency changes, update:
- ADR in `docs/adr/`
- ownership map in `docs/context-ownership.md`
- relevant migration playbook in `docs/migrations/`
