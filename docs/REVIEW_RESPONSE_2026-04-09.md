# Review Response — Intel Documentation Platform

> **Date:** 2026-04-09  
> **Branch:** `audit`  
> **Prepared by:** Yogev  

---

## 1. Client & Internal Views — Image Overview

The platform serves two distinct audiences through separate portals:

### Internal Portal (Management)
- **Dashboard** with analytics widgets — document counts, engagement metrics, recent activity
- **Documents workspace** — list view with status badges (Draft / Active / Archived), category tags, bulk actions
- **Rich text editor** — TipTap-based, Google Docs-style real-time collaboration with live cursors
- **Review queue** — approve/reject pipeline with audience snapshots and drift detection
- **Support desk** — tenant-isolated ticket management with agent assignment
- **AI Assistant** — floating chat bubble available on every page, tool-augmented responses

### Customer Portal (External)
- **Company-scoped document library** — only documents assigned to the customer's company are visible
- **Distraction-free viewer** — published versions with table of contents and print-friendly layout
- **Support tickets** — create, track, and reply to agents
- **Feedback & NPS** — structured feedback forms with tenant-scoped surveys

### Planned Visual Refinements
- [ ] Tighten spacing and card elevation consistency across dashboards
- [ ] Unify color tokens between internal and customer portals (Slate/Sky/Emerald/Rose palette)
- [ ] Improve mobile responsiveness on document list and detail views
- [ ] Add skeleton loaders for all async content areas
- [ ] Review dark mode contrast ratios for WCAG AA compliance

---

## 2. Feedback — Visuals & Functionality

### Current Design System
| Element | Implementation |
|---|---|
| **Typography** | Space Grotesk (headings) + IBM Plex Sans (body) |
| **Color palette** | Slate, Sky, Emerald, Rose — light and dark mode |
| **Components** | TailwindCSS utility classes, consistent card/panel patterns |
| **Icons** | Lucide React icon set |
| **Charts** | Recharts for analytics dashboards |

### Functional Highlights
- **6-tier RBAC** — System Admin → Admin → Manager → Editor → Viewer → Customer
- **Multi-tenancy** — complete tenant isolation enforced at service layer
- **DOCX/PPTX ingestion** — structured extraction preserving headings, tables, lists, images
- **Real-time collaboration** — Hocuspocus (Yjs CRDT) with offline support
- **Full-text search** — FTS5 with autocomplete and faceted filtering

### Areas for Improvement
- [ ] Consolidate loading/error states into reusable patterns
- [ ] Add transition animations between page navigations
- [ ] Improve empty-state illustrations across all list views

---

## 3. First-Entry Checklist & Site Tour (Per Role)

Each role receives an **automatic welcome guide** on first login (or when the guide version is updated). The system tracks state server-side via `UserOnboardingState`:

| Field | Purpose |
|---|---|
| `guide_seen_at` | Timestamp of when the user dismissed the welcome guide |
| `guide_version` | Version number — guide re-opens if this changes |
| `checklist_version` | Tracks which checklist version the user completed |
| `checklist_completed_at` | Timestamp when all steps were finished |

### Welcome Guide Dialog
A modal that opens automatically on first entry showing:
1. **Gradient header** with role-specific title and description
2. **3 "What to expect" cards** tailored to the user's role
3. **Two CTAs** — "Start checklist" (reveals step-by-step tasks) and a role-specific quick-action link

### Role-Specific Checklists

| Role | Steps | Focus Areas |
|---|---|---|
| **Customer** | 4 | Browse documents, Chat, Support tickets, Feedback |
| **Viewer** | 3 | Browse documents, Open document detail, Notification preferences |
| **Editor** | 4 | Create draft, Upload document, Set audience/status, Submit for review |
| **Manager** | 4 | Users & invitations, Approvals queue, Support conversations, Documents |
| **Admin** | 4 | Users & invitations, Company management, Documents & recovery, Review queue |
| **System Admin** | 4 | System setup (SMTP/lifecycle), Users, Admin ops (collab health), Document recovery |

**Versioning:** When the checklist structure changes, the `ONBOARDING_CHECKLIST_VERSION` constant is bumped, which clears all users' completed steps so they see the updated checklist.

---

## 4. Internal AI — Process Tracking Improvements

### Current Architecture
- **Model:** Ollama running llama3.1:8b locally (self-hosted, no external API calls)
- **RAG pipeline:** ChromaDB vector store for document-aware responses
- **Tool-augmented generation:** 29 tools across 7 categories (documents, users, settings, tenants, info, support, feedback)
- **Access control:** Document access policies enforced on every tool call

### Performance (Current State)
| Metric | Value |
|---|---|
| Tool call latency | ~4 seconds |
| Time to first token | ~7 seconds |
| Total response time | ~10–15 seconds |
| GPU utilization | 92% GPU / 8% CPU (NVIDIA reservation) |

### Planned Optimizations
- [ ] **Smart tool routing** — keyword-mapped tool groups send only 5–8 relevant tools per request instead of all 29
- [ ] **Context window tuning** — 4096 tokens for tool calls, 8192 for summaries (vs. default 128K)
- [ ] **Model warm-up** — automatic model loading on app startup (`keep_alive=30m` keeps model in GPU memory)
- [ ] **Process tracking dashboard** — surface AI usage metrics (request count, avg latency, tool hit rates) in the admin analytics section
- [ ] **Conversation history** — full CRUD for conversation management, accessible from both internal and customer portals
- [ ] **Streaming responses** — SSE-based token streaming for real-time output in the chat UI

---

## 5. Docker & Ollama Model — Download Times

### Container Architecture
| Container | Image | Approximate Size |
|---|---|---|
| `v2-backend` | Custom (FastAPI + Python 3.11) | ~500 MB |
| `v2-frontend` | Custom (Node 18 + Vite) | ~300 MB |
| `v2-collab-server` | Custom (Node + Hocuspocus) | ~200 MB |
| `v2-redis` | `redis:7-alpine` | ~30 MB |
| `v2-ollama` | `ollama/ollama` (+ llama3.1:8b model) | ~4.7 GB image + ~4.7 GB model |

### Ollama Download Considerations
- The Ollama container itself is ~4.7 GB; the llama3.1:8b model adds another ~4.7 GB on first pull
- **Total first-run download for AI features: ~9.4 GB**
- Subsequent runs use cached layers — only code changes trigger rebuilds
- The Ollama service uses a Docker **profile** (`ai`), meaning it is **optional** and not downloaded unless explicitly started with `docker compose --profile ai up`

### Mitigations for Download Time
- [ ] Document expected download times in README (estimate ~10–20 min on typical broadband)
- [ ] Provide a `setup.sh` script that pre-pulls the Ollama model in the background while other containers build
- [ ] Consider offering a "lite" mode without AI for demos or low-bandwidth environments
- [ ] Pin image digests (already done) for reproducible builds and layer caching
- [ ] Add download progress indicators to deployment scripts

### Starting Without AI (Fast Start)
```bash
# Standard start (~2-3 min first build, ~10s subsequent)
docker compose up -d

# Full start with AI (~15-20 min first build including model download)
docker compose --profile ai up -d
```

---

## Summary — Action Items

| # | Item | Priority | Status |
|---|---|---|---|
| 1 | Refine visual consistency between portals | Medium | Planned |
| 2 | Document role-based onboarding flows for stakeholder review | High | ✅ Documented above |
| 3 | Add AI process-tracking metrics to admin dashboard | Medium | Planned |
| 4 | Optimize Docker first-run experience (pre-pull scripts, lite mode) | Medium | Planned |
| 5 | Prepare demo walkthrough video showing both portals | Low | Not started |
| 6 | Benchmark Ollama response times on target hardware | High | Planned |
