# Design Migration Plan: Zip A → Zip B Visual Style

## Goal
Make the frontend (Zip A - Vite/React) look identical to the developer-portal-phases-main-master (Zip B - Next.js) **without changing any logic, routes, or API calls**.

---

## Phase 0 — Inject Zip B Design System (SAFE) ✅ IMPLEMENTED

### 0.1 Update Tailwind Config
**File:** `frontend/tailwind.config.js`

Add Zip B's theme extensions:
- `fontFamily.display` = `var(--font-display)`
- `fontFamily.body` = `var(--font-body)`
- Color scales: `slate`, `accent`, `surface`
- `borderRadius`: xl/2xl/3xl
- `boxShadow`: surface, surface-lg

### 0.2 Add Global Component Utility Classes
**File:** `frontend/src/index.css`

Add inside `@layer components { }`:
- `.surface-card`
- `.surface-card-hover`
- `.surface-muted`
- `.surface-contrast`
- `.eyebrow`
- `.section-title`
- `.btn-primary`
- `.btn-secondary`
- `.btn-ghost`
- `.input-field`
- `.select-field`
- `.pill`

### 0.3 Add Fonts
**File:** `frontend/index.html`

Add Google Fonts links:
- Space Grotesk (display)
- IBM Plex Sans (body)

**File:** `frontend/src/index.css`

Add CSS variables:
```css
:root {
  --font-display: "Space Grotesk", sans-serif;
  --font-body: "IBM Plex Sans", sans-serif;
}
```

### 0.4 Update Base Body Styles
**File:** `frontend/src/index.css`

Update body to use Zip B's gradient background and typography.

✅ **Done when:** A test component using `surface-card btn-primary` looks like Zip B.

---

## Phase 1 — Restyle Existing Layouts (NO ROUTE CHANGES)

### 1.1 Keep ALL existing routes as-is
- `/browse`, `/doc/:id`, `/search`
- `/dashboard`, `/documents`, `/reviews`, `/users`, `/analytics`
- `/portal/*`
- `/admin/*`

### 1.2 Update Layout Components (visual only)

**Option A (Closest to Zip B):** Convert sidebar layout to top header navigation
- Update `Layout.tsx` to use PortalHeader-style top nav
- Remove sidebar, keep same nav destinations
- Same auth guards, same page components

**Option B (Lower risk):** Keep sidebar but restyle with Zip B colors/fonts

**Files to update:**
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/Sidebar.tsx` (or remove if Option A)
- `frontend/src/layouts/PublicLayout.tsx`
- `frontend/src/layouts/CustomerLayout.tsx`

✅ **Done when:** Layout has Zip B header + footer, same navigation targets.

---

## Phase 2 — Restyle Shared UI Components

Update existing components with Zip B class names:

| Component Type | Zip B Classes |
|---------------|---------------|
| Buttons | `btn-primary`, `btn-secondary`, `btn-ghost` |
| Inputs | `input-field`, `select-field` |
| Cards | `surface-card`, `surface-card-hover`, `surface-muted` |
| Badges/Pills | `pill` |
| Text | `eyebrow`, `section-title` |

✅ **Done when:** All shared components use Zip B styling.

---

## Phase 3 — Restyle Pages (Same Logic, New Look)

### Public Pages
- `PublicHomePage` → Add hero gradient, keep same data
- `PublicDocumentsPage` → Zip B card layout, same API calls
- `PublicDocumentPage` → Zip B styling, same content rendering
- `PublicSearchPage` → Zip B inputs/layout, same search logic

### Internal Pages
- `DashboardPage` → Zip B cards and spacing
- `DocumentsPage` → Zip B table/card styling
- `DocumentDetailPage` → Zip B layout
- `ReviewsPage` → Zip B styling
- `UsersPage` → Zip B table styling
- `AnalyticsDashboardPage` → Zip B cards
- `FeedbackPage` → Zip B styling
- `CompaniesPage` → Zip B styling

### Customer Portal Pages
- `CustomerDashboard` → Zip B styling
- `CustomerDocumentsPage` → Zip B cards
- `CustomerDocumentPage` → Zip B layout
- `MyFeedbackPage` → Zip B styling

### Login Page
- `LoginPage` → Zip B centered card, colors, button

✅ **Done when:** All pages use Zip B visual language.

---

## Phase 4 — Visual Regression Tests (Optional)

Add Playwright screenshot tests:
- Fixed viewport (1440x900)
- Capture key pages
- Compare to baseline images

---

## What This Plan DOES NOT Change

✅ Same routes (no URL changes)
✅ Same API calls and data fetching
✅ Same auth guards and permissions
✅ Same form handlers and mutations
✅ Same component logic and state

---

## Implementation Order

1. **Phase 0** - Design tokens + CSS utilities + fonts ✅
2. **Phase 1** - Layout shell (header/nav)
3. **Phase 2** - Shared UI components
4. **Phase 3** - Login page (quick win)
5. **Phase 3** - Public pages
6. **Phase 3** - Internal pages
7. **Phase 3** - Customer portal pages
8. **Phase 4** - Visual tests (optional)
