# PERFORMANCE / LOAD AUDIT - 2026-03-26

## 1. Goal

Review the current system for runtime performance and load-readiness, with
focus on:

- concurrency and write contention
- collaboration traffic
- search behavior under load
- assistant / Ollama / RAG flows
- large document and conversion handling

This is not a new security audit. It is a production-readiness audit for
latency, throughput, scaling behavior, and regression detection.

---

## 2. Current Rating

- Concurrency and write isolation: `8.1/10`
- Collaboration traffic readiness: `7.0/10`
- Search performance readiness: `6.7/10`
- Assistant / RAG readiness: `6.8/10`
- Large document handling: `7.4/10`
- Performance/load regression protection: `6.2/10`

### Overall performance/load readiness: `7.0/10`

---

## 3. Bottom Line

The codebase has solid performance building blocks:

- split databases reduce write contention
- the collaboration server has debounce controls and Redis fan-out support
- search has projection caching and benchmark scenarios
- assistant HTTP clients reuse connections
- conversion work has a durable retryable worker path

But this is not yet a `10/10` load-ready base.

The biggest gap is not "obvious slow code." The biggest gap is that the system
still lacks production-faithful load validation and hard runtime guardrails for
the heaviest flows. Today, the project is good at correctness and structural
quality, but still only partially proven under real concurrency and sustained
traffic.

---

## 4. Findings Summary

| ID | Severity | Finding | Area |
|----|----------|---------|------|
| `PL-01` | High | No production-faithful load gate or performance regression gate | Tooling / CI |
| `PL-02` | High | Search path is SQLite-FTS-first and silently degrades to LIKE | Search |
| `PL-03` | High | Assistant capacity is not bulkheaded and a single request can fan out into multiple LLM calls | Assistant |
| `PL-04` | Medium | Collaboration runtime lacks stronger traffic guardrails and useful saturation telemetry | Collaboration |
| `PL-05` | Medium | Large-document handling is bounded mainly by rejection/truncation, not streaming architecture | Documents / Uploads |
| `PL-06` | Medium | Reader artifact generation can still fall back to daemon-thread execution | Conversion |
| `PL-07` | Medium | SLO coverage exists, but does not cover the main performance hotspots from this audit | Observability |

---

## 5. Detailed Findings

### `PL-01` High: No production-faithful load gate or performance regression gate

#### Evidence

- [load_test_collaboration.py](C:/Users/yogev/finale_project/scripts/load_test_collaboration.py) exists, but it is a local script, not a CI gate.
- That script generates its own mock JWT using the insecure test secret and sends synthetic JSON payloads instead of real editor/Yjs client behavior.
- [ci.yml](C:/Users/yogev/finale_project/.github/workflows/ci.yml) has no load/performance stage.
- [check-bundle-budget.mjs](C:/Users/yogev/finale_project/frontend/scripts/check-bundle-budget.mjs) exists, but it is not wired into CI either.

#### Why this matters

The repo has tests and some micro-benchmark style checks, but it does not have a
repeatable, production-relevant performance gate that would catch:

- collaboration saturation regressions
- assistant throughput collapse
- search degradation after query/index changes
- upload/conversion backlog growth

So performance can regress without breaking correctness tests.

#### What closes it

- Add a dedicated CI-visible performance stage for:
  - collaboration traffic
  - assistant chat throughput
  - search latency on seeded data
  - conversion backlog drain behavior
- Replace the current synthetic collab harness with a real protocol-faithful one
  that uses backend-issued tokens and real editor/Yjs traffic.

---

### `PL-02` High: Search path is SQLite-FTS-first and silently degrades to LIKE

#### Evidence

- [search_index_service.py](C:/Users/yogev/finale_project/backend/app/services/search_index_service.py) is explicitly built around SQLite virtual FTS5 tables (`sqlite_master`, `PRAGMA table_info`, `CREATE VIRTUAL TABLE ... USING fts5`).
- [search_queries.py](C:/Users/yogev/finale_project/backend/app/application/queries/search_queries.py) issues `documents_fts MATCH :search_query`.
- On `OperationalError` / `ProgrammingError`, search falls back to a `LIKE` query path instead of a database-native indexed search path.
- [DEPLOYMENT.md](C:/Users/yogev/finale_project/docs/DEPLOYMENT.md) documents PostgreSQL as the production database.

#### Why this matters

This creates a serious predictability problem:

- local/dev search performance can look good on SQLite FTS5
- production behavior can be materially different on PostgreSQL
- if the FTS path is unavailable, the system silently falls back to a much less
  scalable `LIKE` path

That is acceptable as a safety fallback, but not as the primary production load story.

#### What closes it

- Make the production search path explicit:
  - either commit to SQLite-only search for deployed environments
  - or implement and benchmark a PostgreSQL-native indexed search path
- Treat `LIKE` fallback as degraded mode only, with health/metrics visibility.

---

### `PL-03` High: Assistant capacity is not bulkheaded and a single request can fan out into multiple LLM calls

#### Evidence

- [assistant.py](C:/Users/yogev/finale_project/backend/app/api/management/assistant.py) rate-limits per user, but there is no global concurrency semaphore or queue for the assistant subsystem.
- [engine.py](C:/Users/yogev/finale_project/backend/app/assistant/engine.py) can trigger multiple model interactions per user message:
  - tool routing
  - initial tool-selection chat
  - summary streaming after tool execution
  - follow-up suggestion generation
  - title generation
  - auto-summarization for long conversations
- [tool_router.py](C:/Users/yogev/finale_project/backend/app/assistant/tool_router.py) uses embedding-based routing, which adds more embedding requests.
- [ollama_client.py](C:/Users/yogev/finale_project/backend/app/assistant/ollama_client.py) uses a shared client pool, but the pool is only `max_connections=10`, which is not the same thing as admission control.
- [embeddings.py](C:/Users/yogev/finale_project/backend/app/assistant/rag/embeddings.py) retries embedding calls, which is good for resilience but can amplify latency under provider stress.

#### Why this matters

Under light traffic, this is fine.

Under moderate concurrent assistant usage, a few user requests can monopolize
the single inference backend and create:

- request pile-ups
- long tail latency
- retry amplification
- mixed contention between chat and embedding traffic

The current design is correctness-safe but not load-safe enough for `10/10`.

#### What closes it

- Add a global assistant admission-control layer:
  - max concurrent chats
  - max concurrent embedding jobs
  - explicit queue length / rejection behavior
- Separate chat and embedding capacity accounting.
- Add assistant p50/p95 and saturation metrics that are visible in health/ops dashboards.

---

### `PL-04` Medium: Collaboration runtime lacks stronger traffic guardrails and useful saturation telemetry

#### Evidence

- [collabServerApp.ts](C:/Users/yogev/finale_project/collab-server/src/server/collabServerApp.ts) has useful debounce settings and optional Redis scaling, but no max-connections policy, no per-document traffic caps, and no awareness throttling.
- [connectionRegistry.ts](C:/Users/yogev/finale_project/collab-server/src/server/connectionRegistry.ts) tracks active documents and total connections, but not per-document hot spots, reconnect churn, load/save latency, or failed persistence counts.
- [healthServer.ts](C:/Users/yogev/finale_project/collab-server/src/server/healthServer.ts) exposes only basic health/readiness info.
- [load_test_collaboration.py](C:/Users/yogev/finale_project/scripts/load_test_collaboration.py) is not protocol-faithful enough to prove real editor traffic behavior.

#### Why this matters

The collaboration runtime is likely fine for current usage, but when traffic spikes
there is limited visibility into:

- which documents are hot
- whether persistence is saturating
- whether reconnect storms are occurring
- whether awareness traffic is overwhelming the server

That makes tuning and incident response harder than it should be.

#### What closes it

- Add collab metrics for:
  - load/save latency
  - failed save count
  - per-document connection count
  - reconnect rate
  - persistence-failure active-doc count
- Add explicit connection / document hot-spot guardrails.
- Replace the current synthetic load harness with a real client-driven one.

---

### `PL-05` Medium: Large-document handling is bounded mainly by rejection/truncation, not streaming architecture

#### Evidence

- [config.py](C:/Users/yogev/finale_project/backend/app/config.py) sets `MAX_UPLOAD_SIZE` to `10MB`.
- [file_handler.py](C:/Users/yogev/finale_project/backend/app/assistant/file_handler.py) reads the entire upload into memory with `await file.read()`.
- The same file caps PDF extraction to `100` pages and truncates extracted text to `50,000` characters.
- [upload.py](C:/Users/yogev/finale_project/backend/app/services/attachment_service/upload.py) computes checksum and uploads using in-memory bytes, not streamed chunk-by-chunk processing.
- [pdf_to_docx.py](C:/Users/yogev/finale_project/backend/app/conversion/pdf_to_docx.py) opens the full PDF byte stream in memory.

#### Why this matters

This is not unsafe. In fact, the hard caps are a good protective measure.

But it means the current large-document story is:

- reject larger inputs
- truncate deeper extraction
- keep the in-memory path simple

That is a valid product choice, but it is not a `10/10` load architecture for
heavy document ingestion.

#### What closes it

- Decide whether `10MB` is the intended permanent product boundary.
- If larger files must be supported later, move toward:
  - streaming upload paths
  - worker-first extraction
  - explicit per-file processing metrics
  - queue-based backpressure for conversion/extraction

---

### `PL-06` Medium: Reader artifact generation can still fall back to daemon-thread execution

#### Evidence

- [reader_view.py](C:/Users/yogev/finale_project/backend/app/services/attachment_service/reader_view.py) uses `threading.Thread(..., daemon=True)` when `background_tasks` is absent.
- [conversion_jobs.py](C:/Users/yogev/finale_project/backend/app/services/conversion_jobs.py) provides the durable queue/worker path, which is the stronger design.
- The codebase therefore has both:
  - a proper durable worker path
  - a request-adjacent thread fallback path

#### Why this matters

Under burst traffic, thread-per-request fallback is harder to reason about:

- it is less observable
- it is less bounded
- it is easier to overload than the durable worker

This is not a correctness bug. It is a load-shaping weakness.

#### What closes it

- Make durable conversion jobs the only production path.
- Reserve thread fallback for tests/dev only, or remove it entirely.

---

### `PL-07` Medium: SLO coverage exists, but does not cover the main performance hotspots from this audit

#### Evidence

- [use-case-slos.json](C:/Users/yogev/finale_project/docs/slo/use-case-slos.json) currently covers only:
  - review approval
  - publish approved version
  - analytics overview
- It does not define SLOs for:
  - collaboration connect/save/reconnect
  - internal search latency
  - assistant response latency
  - conversion backlog drain time
  - upload-to-reader-artifact completion time

#### Why this matters

The observability framework is real, but it is not yet aimed at the highest-load
subsystems. That means the project has a burn-rate engine without enough
performance objectives for the areas most likely to hurt users first.

#### What closes it

- Add SLOs for:
  - collaboration session start and save
  - search query latency
  - assistant first-token and full-response latency
  - conversion job completion latency
  - upload-to-reader-view readiness

---

## 6. Strengths

- [test_write_contention.py](C:/Users/yogev/finale_project/backend/tests/test_write_contention.py) shows the split-database write-isolation concern is actively tested.
- [audience_benchmarks.py](C:/Users/yogev/finale_project/backend/tests/scenarios/audience_benchmarks.py) gives the search/audience path a seeded benchmark scenario.
- [ollama_client.py](C:/Users/yogev/finale_project/backend/app/assistant/ollama_client.py) reuses pooled HTTP connections instead of creating per-request clients.
- [engine.py](C:/Users/yogev/finale_project/backend/app/assistant/engine.py) trims prompt context to fit model limits instead of letting context growth run away.
- [conversion_jobs.py](C:/Users/yogev/finale_project/backend/app/services/conversion_jobs.py) already provides a durable retryable worker with DLQ-style handling.
- [collabServerApp.ts](C:/Users/yogev/finale_project/collab-server/src/server/collabServerApp.ts) already has debounce controls and optional Redis support for horizontal collaboration cache invalidation.

---

## 7. Verification Performed

This audit was mainly static/runtime-path analysis, not a full benchmark run.

I did verify the current performance support surface by running:

```bash
cd backend
pytest tests/test_observability_slo.py tests/test_write_contention.py -q
```

Result:

- `5 passed`

This confirms that:

- the SLO evaluation framework is active
- the write-contention benchmark tests are present and passing

It does **not** prove real production throughput or latency under sustained traffic.

---

## 8. Recommended Execution Order

### Phase 1: Highest-value load readiness work

1. `PL-02` Make search production-explicit instead of SQLite-first with silent `LIKE` degradation.
2. `PL-03` Add assistant bulkheads, concurrency caps, and queue/saturation metrics.
3. `PL-01` Add real performance/load gates and a protocol-faithful collab load harness.

### Phase 2: Collaboration and document-path hardening

4. `PL-04` Add collab saturation telemetry and document hot-spot guardrails.
5. `PL-06` Remove daemon-thread fallback from reader artifact generation in production.
6. `PL-05` Decide whether `10MB` is the permanent product boundary or whether streaming/worker-first large-document support is required.

### Phase 3: Observability maturity

7. `PL-07` Expand SLO coverage to collaboration, search, assistant, and conversion flows.

---

## 9. Exit Criteria For Calling Performance / Load Readiness `10/10`

Do not call this area `10/10` until all of the following are true:

- production search path is explicit and benchmarked on the actual target database
- assistant traffic has global concurrency control and clear saturation behavior
- collaboration traffic is exercised by a realistic load harness
- CI contains at least one repeatable performance regression gate
- collab/search/assistant/conversion have real latency and saturation metrics
- request-adjacent thread fallback is removed from production conversion paths
- large-document handling limits are an intentional product decision, not just an implementation shortcut

---

## 10. Recommendation

Do not start another broad code audit before fixing this area.

The next best move is execution, in this order:

1. search production path
2. assistant bulkheads
3. real load gates

That sequence will move the platform from "good codebase with partial load proof"
to "good codebase with credible runtime proof."
