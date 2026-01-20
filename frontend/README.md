# Document Portal V2 - Frontend

React 18 + TypeScript 5 + Vite 5 + TailwindCSS 3

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Frontend will be available at http://localhost:3000

## Build

```bash
npm run build
```

## Testing

```bash
# Unit tests
npm test

# Unit tests with UI
npm run test:ui

# E2E tests
npm run test:e2e
```

## Code Quality

```bash
# Lint
npm run lint

# Format
npm run format
```

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx           # Entry point
│   ├── App.tsx            # Root component
│   ├── components/        # Reusable components
│   ├── pages/             # Page components
│   ├── lib/               # Utilities & API client
│   └── types/             # TypeScript types
├── public/                # Static assets
└── index.html             # HTML template
```
