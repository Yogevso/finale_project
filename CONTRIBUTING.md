# Contributing to Documentation Platform

## Branch Strategy

- `main` - Production-ready code only
- `develop` - Integration branch for features
- `feature/<name>` - Feature branches (e.g., `feature/attachments-api`)
- `fix/<name>` - Bug fix branches (e.g., `fix/login-redirect`)

## Development Workflow

1. Create a feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

3. Push and create a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, no code change
- `refactor:` - Code restructuring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add document versioning API
fix: resolve 401 redirect loop
docs: update API documentation
test: add auth service unit tests
```

## Code Style

### Backend (Python)
- Use `ruff` for linting and formatting
- Type hints required for all functions
- Follow PEP 8 naming conventions

### Frontend (TypeScript)
- Use ESLint + Prettier
- Functional components with hooks
- TailwindCSS for styling

## Testing

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm run lint
npm run test -- --run
```

### Collaboration Server
```bash
cd collab-server
npm run lint
npm run test
```

## PR Review Workflow

Use the PR comment triage script before requesting re-review:

```bash
# Requires GitHub CLI (gh) and gh auth login
python scripts/fetch_pr_comments.py
```

## Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Unresolved PR review comments are addressed or acknowledged
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] No console.log or print statements left
- [ ] Branch is up to date with `develop`

## Getting Help

- Check existing issues before creating new ones
- Use descriptive titles for issues/PRs
- Include steps to reproduce for bugs
