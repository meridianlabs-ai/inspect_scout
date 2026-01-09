# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure
- Python backend: `src/inspect_scout/`
- React frontend: `src/inspect_scout/_view/www/`

## Python

### Commands
- Test: `pytest` / `pytest tests/path/to/test.py::func -v`
- Lint: `ruff check --fix`
- Format: `ruff format`
- Type check: `mypy src examples tests`
- All checks: `make check`

### Style
- Google style convention, ruff formatting
- isort import order (enforced by ruff)
- Strict typing required - all functions annotated, including tests
- snake_case for vars/funcs/methods; PascalCase for classes
- Google-style docstrings for public APIs

## TypeScript (run from `src/inspect_scout/_view/www/`)

### Setup
```bash
corepack enable  # once
pnpm install
```

### Commands
- Dev: `pnpm dev`
- Build: `pnpm build`
- Lint: `pnpm lint` / `pnpm lint:fix`
- Format: `pnpm format`
- Type check: `pnpm typecheck`
- All checks: `pnpm check`
- Test: `pnpm test`

### Style
- Strict mode enabled
- Avoid `any` and type assertions
- ESLint + Prettier

## Type Sharing (Python → TypeScript)

Pipeline: Pydantic models → openapi.json → generated.ts

After Python API changes:
1. `.venv/bin/python scripts/export_openapi_schema.py`
2. `pnpm build` (regenerates types)
3. Commit both `openapi.json` and `src/types/generated.ts`

Manual type generation: `pnpm types:generate`

CI validates both files stay in sync.

## General Guidelines
- Use appropriate exception types; include context in error messages
- Respect existing code patterns when modifying files
- Run linting before committing changes
- Maintain high test coverage
