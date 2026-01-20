# Document Portal V2 - Frontend

Modern React SPA with TypeScript, Vite, TailwindCSS, and TipTap rich text editor.

---

## 🚀 Features

### User Interface
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Dark/Light Mode** - System preference detection (coming soon)
- **Accessible** - ARIA labels, keyboard navigation
- **Fast** - Vite HMR, optimized builds

### Management Portal
- **Dashboard** - Overview of recent documents, stats
- **Document List** - Paginated, searchable, filterable
- **Document Editor** - Rich text editing with TipTap
- **Version Management** - Create, view, publish versions
- **File Attachments** - Drag & drop upload, download
- **Comments** - Threaded discussions, inline comments
- **User Management** - CRUD for users (admin only)

### Viewer Portal
- **Public Access** - No login required
- **Clean Reading** - Distraction-free document viewing
- **Navigation** - Table of contents, version selection

### Components
- **NotificationBell** - Real-time notification dropdown
- **RichTextEditor** - TipTap with headings, lists, links, tables
- **CommentsSection** - Threaded comments with replies
- **VersionsSection** - Version history and publishing
- **AttachmentsSection** - File upload and management
- **EngagementBar** - Bookmarks, feedback, progress

---

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | React 18 |
| Language | TypeScript 5 |
| Build Tool | Vite 5 |
| Styling | TailwindCSS 3 |
| Icons | Lucide React |
| Rich Text | TipTap 2 |
| HTTP Client | Fetch API |
| Routing | React Router 6 |
| Testing | Vitest + Playwright |
| Linting | ESLint + TypeScript ESLint |

---

## 🛠️ Setup

### Prerequisites
- Node.js 20+
- npm 10+

### Installation

```bash
npm install
```

---

## ⚙️ Configuration

Create a `.env` file:

```env
# API Backend URL
VITE_API_URL=http://localhost:8001

# Application
VITE_APP_NAME=Document Portal
VITE_APP_VERSION=2.0.0
```

---

## 🏃 Running

### Development Server

```bash
npm run dev
```

Frontend available at http://localhost:5173

### Production Build

```bash
npm run build
npm run preview  # Preview production build
```

---

## 🧪 Testing

```bash
# Run unit tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Run E2E tests (Playwright)
npm run test:e2e

# Run E2E tests headed (see browser)
npm run test:e2e -- --headed
```

---

## 🔍 Code Quality

```bash
# Lint code
npm run lint

# Fix lint issues
npm run lint -- --fix

# Type check
npm run type-check

# Format with Prettier (if configured)
npm run format
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── main.tsx                 # Application entry point
│   ├── App.tsx                  # Root component with routing
│   ├── index.css                # Global styles + Tailwind
│   │
│   ├── components/              # Reusable UI components
│   │   ├── Layout.tsx           # Main layout wrapper
│   │   ├── Header.tsx           # Top navigation bar
│   │   ├── Sidebar.tsx          # Side navigation menu
│   │   ├── NotificationBell.tsx # Notification dropdown
│   │   ├── DocumentEditor.tsx   # Document form + editor
│   │   ├── RichTextEditor.tsx   # TipTap editor wrapper
│   │   ├── CommentsSection.tsx  # Comments list + form
│   │   ├── VersionsSection.tsx  # Version history
│   │   ├── AttachmentsSection.tsx # File attachments
│   │   └── EngagementBar.tsx    # Bookmark, feedback, progress
│   │
│   ├── pages/                   # Page components
│   │   ├── LoginPage.tsx        # Login form
│   │   ├── DashboardPage.tsx    # Main dashboard
│   │   ├── DocumentsPage.tsx    # Document list
│   │   ├── DocumentDetailPage.tsx # Document view/edit
│   │   ├── UsersPage.tsx        # User management
│   │   └── viewer/              # Public viewer pages
│   │       ├── ViewerHomePage.tsx
│   │       └── ViewerDocumentPage.tsx
│   │
│   ├── lib/                     # Utilities
│   │   ├── api.ts               # API client with auth
│   │   ├── auth.ts              # Auth context & hooks
│   │   └── utils.ts             # Helper functions
│   │
│   └── types/                   # TypeScript definitions
│       └── index.ts             # Shared types
│
├── public/                      # Static assets
│   └── favicon.ico
│
├── tests/                       # Test files
│   ├── *.test.ts               # Vitest unit tests
│   └── e2e/                    # Playwright E2E tests
│
├── index.html                   # HTML template
├── vite.config.ts               # Vite configuration
├── tailwind.config.js           # TailwindCSS configuration
├── tsconfig.json                # TypeScript configuration
├── eslint.config.js             # ESLint configuration
├── playwright.config.ts         # Playwright configuration
├── package.json                 # Dependencies & scripts
├── Dockerfile                   # Production Docker image
├── Dockerfile.dev               # Development Docker image
├── nginx.conf                   # Nginx config for Docker
└── README.md
```

---

## 🎨 Styling

### TailwindCSS Classes

Common patterns used:

```tsx
// Card
<div className="bg-white rounded-lg shadow-md p-6">

// Button Primary
<button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">

// Button Secondary
<button className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg">

// Input
<input className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500">

// Badge
<span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
```

### Color Palette

| Color | Usage |
|-------|-------|
| Blue-600 | Primary actions, links |
| Green-600 | Success, published |
| Yellow-500 | Warning, draft |
| Red-600 | Error, delete |
| Gray-100/200 | Backgrounds |
| Gray-700/800 | Text |

---

## 📡 API Integration

### API Client (`src/lib/api.ts`)

```typescript
import { api } from './lib/api';

// GET request
const documents = await api.get('/documents');

// POST request
const newDoc = await api.post('/documents', { title: 'New Doc' });

// PUT request
await api.put(`/documents/${id}`, { title: 'Updated' });

// DELETE request
await api.delete(`/documents/${id}`);

// File upload
await api.upload(`/documents/${id}/attachments`, file);
```

### Authentication

```typescript
import { useAuth } from './lib/auth';

function Component() {
  const { user, login, logout, isAuthenticated } = useAuth();
  
  // Check role
  if (user?.role === 'admin') {
    // Show admin features
  }
}
```

---

## 🐳 Docker

### Build Image

```bash
docker build -t document-portal-frontend:latest .
```

### Run Container

```bash
docker run -p 3000:80 document-portal-frontend:latest
```

### Development with Docker

```bash
docker build -f Dockerfile.dev -t frontend-dev .
docker run -p 5173:5173 -v $(pwd)/src:/app/src frontend-dev
```

---

## 🔧 VS Code Setup

### Recommended Extensions
- ESLint
- Tailwind CSS IntelliSense
- TypeScript Vue Plugin (Volar) - for better TS support
- Prettier (optional)

### Settings (`.vscode/settings.json`)

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "tailwindCSS.includeLanguages": {
    "typescript": "javascript",
    "typescriptreact": "javascript"
  }
}
```

---

## 📝 License

MIT License - See [LICENSE](../LICENSE) for details.
