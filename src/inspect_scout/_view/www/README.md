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

### How It Works

The type generation pipeline:
```
Python Pydantic models → openapi.json → generated.ts → built app
```

1. **Export schema**: Python script exports OpenAPI spec from FastAPI to `openapi.json`
2. **Generate types**: `openapi-typescript` generates TypeScript types from schema
3. **Type adapter**: `src/types/api-types.ts` re-exports types with clean names
4. **Usage**: Import types from `src/types/index.ts` in your code

### Updating Types After API Changes

When Python Pydantic models change:

```bash
# 1. Export updated OpenAPI schema
.venv/bin/python scripts/export_openapi_schema.py

# 2. Types regenerate automatically on next build
pnpm build
```

Commit both `openapi.json` and `src/types/generated.ts`.

### Manual Type Generation

```bash
pnpm types:generate
```

### CI Validation

CI automatically validates the type generation pipeline:

- **`openapi-schema` job**: Regenerates `openapi.json` and fails if it differs from committed version
- **`js-build` job**: Regenerates `generated.ts` and fails if it differs from committed version

If CI fails, run the commands shown in the error message and commit the updated files.

## Tech Stack

- React 19
- TypeScript
- Vite
- Bootstrap 5
- AG Grid
- React Router
