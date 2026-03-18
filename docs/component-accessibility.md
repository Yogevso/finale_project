# Component Accessibility Documentation (AC-017)

This document describes the accessibility patterns used in each major component category.

## Layout Components

### Layout.tsx / PublicLayout.tsx / CustomerLayout.tsx
- **Skip navigation**: `<SkipNavLink />` is the first child, linking to `#main-content`
- **Main landmark**: `<main id="main-content">` provides the skip target
- **Mobile toggle**: Has `aria-label` and `aria-expanded` attributes
- **Route announcements**: `<RouteChangeAnnouncer />` in App.tsx announces page changes via `aria-live="polite"`

## Modal / Dialog Components

All modals follow a consistent pattern:

```tsx
import { useFocusTrap } from '@/hooks/useAccessibility'

function MyModal({ onClose }) {
  const { containerRef, handleKeyDown } = useFocusTrap(onClose)
  return (
    <div className="fixed inset-0 …" onClick={onClose}>
      <div ref={containerRef} role="dialog" aria-modal="true" aria-label="…"
           onClick={e => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <button aria-label="Close …"><X /></button>
        {/* content */}
      </div>
    </div>
  )
}
```

**Components using this pattern:**
- AdvancedSearchModal, InviteUserDialog, ReviewDialog, FeedbackResponseDialog
- VisibilityChangeConfirmDialog, CompanyForm, AdminFirstCompanyWizard
- UploadDocumentModal, CreateDocumentModal, QuickStartModal, BulkMetadataEditModal
- SectionEditPopup, ReviewSubmitModal, ContentEditChooserPopup
- NewChatModal, GroupSettingsModal, AddPeopleModal
- ImageLightbox (also uses `createPortal`)
- SupportPage (AssignAgentModal, HandoffModal)

## Form Components

### Label Association
All form fields use explicit `htmlFor`/`id` binding:
```tsx
<label htmlFor="field-id">Label</label>
<input id="field-id" … />
```

### Error Linking (AC-011)
Forms with validation use `aria-invalid` and `aria-describedby`:
```tsx
<input aria-invalid={!!error} aria-describedby={error ? 'field-error' : undefined} />
{error && <p id="field-error">{error}</p>}
```

### Error Announcements
Error containers use `role="alert"` for immediate screen reader announcement.

## Notification Components

### NotificationBell
- Bell button has `aria-label="Notifications"`
- Unread count badge has `aria-live="polite"` and `role="status"`

### OfflineIndicator
- Root element has `role="status"` and `aria-live="polite"` for connection state changes

### Toaster (sonner)
- sonner library handles ARIA announcements for toast notifications automatically

## Design System (index.css)

### Focus Indicators
All interactive elements have visible focus rings:
```css
.btn-primary, .btn-secondary, .btn-ghost {
  @apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2;
}
```

### Color Contrast
- `.eyebrow` uses `text-slate-600` (meets 4.5:1 ratio)
- All text colors meet WCAG AA minimums against their backgrounds

### High Contrast Mode (AC-012)
```css
@media (forced-colors: active) {
  .surface-card, .surface-muted { border: 1px solid CanvasText; }
  .btn-primary, .btn-secondary, .btn-ghost { border: 1px solid ButtonText; }
  input, select, textarea { border: 1px solid CanvasText; }
}
```
