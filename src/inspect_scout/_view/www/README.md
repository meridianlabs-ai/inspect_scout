# Inspect Scout Viewer

A React-based web viewer for Inspect AI evaluation logs.

## Prerequisites

This project uses [pnpm](https://pnpm.io/) as its package manager, managed through [corepack](https://nodejs.org/api/corepack.html).

### Setup

**Enable corepack** (required once):
```bash
corepack enable
```

That's it! Corepack is built into Node.js 16.9+ and will automatically install the correct pnpm version (specified in `package.json`) when you run pnpm commands.

**Alternative:** If you prefer to install pnpm manually, see the [official pnpm installation guide](https://pnpm.io/installation).

### Install Dependencies

```bash
pnpm install
```

## Development

Start the development server:

```bash
pnpm dev
```

Build for production:

```bash
pnpm build
```

Watch mode for development:

```bash
pnpm watch
```

Preview production build:

```bash
pnpm preview
```

## Code Quality

Run linting:

```bash
pnpm lint
```

Auto-fix linting issues:

```bash
pnpm lint:fix
```

Format code:

```bash
pnpm format
```

Check formatting:

```bash
pnpm format:check
```

Type check:

```bash
pnpm typecheck
```

Run all checks (lint, format, typecheck):

```bash
pnpm check
```

## TypeScript Types from OpenAPI

Types are auto-generated from the FastAPI OpenAPI spec to keep client/server in sync.

### Updating Types After API Changes

When Python Pydantic models change:

```bash
# 1. Export updated OpenAPI schema
.venv/bin/python scripts/export_openapi_schema.py

# 2. Types regenerate automatically on next build
pnpm build
```

Types generate via `prebuild` hook, no manual step needed during normal development.

### Manual Type Generation

```bash
pnpm types:generate
```

## Tech Stack

- React 19
- TypeScript
- Vite
- Bootstrap 5
- AG Grid
- React Router
