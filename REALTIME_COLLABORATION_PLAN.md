# Real-Time Collaborative Editing Implementation Plan

**Feature**: Google Docs-style real-time collaboration  
**Status**: 📋 PLANNED  
**Estimated Time**: 23-35 hours  
**Priority**: High  

---

## Overview

Implement full real-time collaboration using TipTap + Yjs for the frontend and Hocuspocus as the collaboration server. Users will see each other's cursors, edits appear instantly, and conflicts are automatically resolved.

---

## Architecture

┌─────────────────────────────────────────────────────────────────────────────┐
│ COLLABORATION ARCHITECTURE │
├─────────────────────────────────────────────────────────────────────────────┤
│ │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ Browser 1 │ │ Browser 2 │ │ Browser 3 │ │
│ │ (John) │ │ (Sarah) │ │ (Mike) │ │
│ │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │ │
│ │ │ TipTap │ │ │ │ TipTap │ │ │ │ TipTap │ │ │
│ │ │ + Yjs │ │ │ │ + Yjs │ │ │ │ + Yjs │ │ │
│ │ └────┬───┘ │ │ └────┬───┘ │ │ └────┬───┘ │ │
│ └───────┼──────┘ └───────┼──────┘ └───────┼──────┘ │
│ │ WebSocket │ WebSocket │ │
│ └─────────────────────┼─────────────────────┘ │
│ ▼ │
│ ┌────────────────────────┐ │
│ │ HOCUSPOCUS │ Port 8002 │
│ │ (Node.js Server) │ │
│ └───────────┬────────────┘ │
│ │ HTTP │
│ ▼ │
│ ┌────────────────────────┐ │
│ │ FASTAPI BACKEND │ Port 8001 │
│ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘



---

## Steps

### Step 1: Set Up Hocuspocus Collaboration Server (4-6 hrs)
- [ ] 1.1 Create `v2/collab-server/` directory with package.json
- [ ] 1.2 Install dependencies (@hocuspocus/server, yjs, jsonwebtoken, axios)
- [ ] 1.3 Create server entry point (src/index.ts) on port 8002
- [ ] 1.4 Implement JWT authentication hook (src/auth.ts)
- [ ] 1.5 Implement document persistence hook (src/persistence.ts)
- [ ] 1.6 Implement presence/awareness handling
- [ ] 1.7 Add Dockerfile

### Step 2: Extend FastAPI Backend (2-3 hrs)
- [ ] 2.1 Create `app/api/management/collaboration.py` with endpoints
- [ ] 2.2 Add `yjs_state` BLOB field to Document model
- [ ] 2.3 Create collaboration_service.py (Yjs ↔ HTML conversion)
- [ ] 2.4 Add `POST /auth/collab-token` endpoint

### Step 3: Update Frontend TipTap Editor (4-6 hrs)
- [ ] 3.1 Install: yjs, y-websocket, @tiptap/extension-collaboration, @tiptap/extension-collaboration-cursor
- [ ] 3.2 Create `hooks/useCollaboration.ts`
- [ ] 3.3 Update DocumentEditor.tsx with collaboration extensions
- [ ] 3.4 Create CollaborationStatus.tsx (connection indicator)
- [ ] 3.5 Create CollaboratorCursors.tsx (user cursors)
- [ ] 3.6 Create `lib/userColors.ts` (color assignment)

### Step 4: Implement Presence & Awareness (2-3 hrs)
- [ ] 4.1 Set up Yjs awareness protocol
- [ ] 4.2 Create `stores/collaborationStore.ts`
- [ ] 4.3 Add presence UI (avatars, user count)
- [ ] 4.4 Handle user join/leave notifications

### Step 5: Implement Offline Support (2-3 hrs)
- [ ] 5.1 Add IndexedDB persistence (y-indexeddb)
- [ ] 5.2 Handle connection interruptions with auto-reconnect
- [ ] 5.3 Add conflict resolution UI

### Step 6: Add Permission Controls (1-2 hrs)
- [ ] 6.1 Check user role on WebSocket connection
- [ ] 6.2 Add read-only mode for viewers
- [ ] 6.3 Handle permission changes during session

### Step 7: Add Activity Tracking (2-3 hrs)
- [ ] 7.1 Create CollaborationSession model
- [ ] 7.2 Create ActivityFeed.tsx component
- [ ] 7.3 Integrate with audit logs

### Step 8: Update Version System (2-3 hrs)
- [ ] 8.1 Add "Create Version" button during collaboration
- [ ] 8.2 Implement auto-save versions (every X minutes)
- [ ] 8.3 Add version restore during collaboration

### Step 9: Testing (3-4 hrs)
- [ ] 9.1 Unit tests for collab server
- [ ] 9.2 Integration tests (FastAPI ↔ Hocuspocus)
- [ ] 9.3 E2E tests with Playwright (2 browsers)
- [ ] 9.4 Load testing (10-50 users)

### Step 10: Deployment (1-2 hrs)
- [ ] 10.1 Add environment variables
- [ ] 10.2 Update docker-compose.yml
- [ ] 10.3 Configure Redis for scaling (optional)

---

## Dependencies

**Collab Server (package.json):**
```json
{
  "dependencies": {
    "@hocuspocus/server": "^2.0.0",
    "@hocuspocus/extension-database": "^2.0.0",
    "jsonwebtoken": "^9.0.0",
    "axios": "^1.6.0",
    "yjs": "^13.6.0"
  }
}

Frontend:
npm install yjs y-websocket y-indexeddb @tiptap/extension-collaboration @tiptap/extension-collaboration-cursor

Progress Log
Date	Step	Notes