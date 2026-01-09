# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure
- Python backend: `src/inspect_scout/`
- React frontend: `src/inspect_scout/_view/www/`

## Python

### Commands
- Run all tests: `pytest`
- Run a single test: `pytest tests/path/to/test_file.py::test_function_name -v`
- Format code: `ruff format`
- Lint code: `ruff check --fix`
- Type check: `mypy src examples tests`
- All checks: `make check`

### Style
- **Formatting**: Follow Google style convention. Use ruff for formatting
- **Imports**: Use isort order (enforced by ruff)
- **Types**: Strict typing is required. All functions must have type annotations, including functions in tests.
- **Naming**: Use snake_case for variables, functions, methods; PascalCase for classes
- **Docstrings**: Google-style docstrings required for public APIs
- **Error Handling**: Use appropriate exception types; include context in error messages
- **Testing**: Write tests with pytest; maintain high coverage

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

Respect existing code patterns when modifying files. Run linting before committing changes.
