# AGENTS.md

## Repository Structure
- **Python package** (`src/inspect_scout/`) - Core library for analyzing LLM evaluation transcripts. Provides a CLI, programmatic API, and FastAPI server. Handles transcript databases, scanners, validation, and results.
- **React frontend** (`src/inspect_scout/_view/frontend/`) - TypeScript monorepo (Turborepo + pnpm workspaces) for the web UI. See its own [CLAUDE.md](src/inspect_scout/_view/frontend/CLAUDE.md).

## Principles

- Shortcuts become someone else's problem; hacks compound into debt
- Patterns get copied—establish good ones
- Flag issues; ask before fixing
- Strict typing required
  - Python: modern syntax (`X | None`, `dict[str, Any]`)
  - TypeScript: no `any`, no type assertions
- Error handling: appropriate exceptions with context
- Respect existing patterns
- Before committing, run the appropriate checks for code you touched (lint, typecheck, test)

### Testing
- Test observable behavior, not internal implementation details
- Do not test things that are enforced by the type system
- Be efficient; avoid duplicate coverage
- Prefer data/table driven tests for maintainability
- Tests must be isolated; no shared mutable state or order dependencies
- Tests must be deterministic; control randomness with seeds
- Prefer real objects over mocks when possible

### Common Pitfalls
- Stay within scope—don't make unrequested changes
- Never edit generated files—`openapi.json` and `generated.ts` are generated; modify source and regenerate
- During development, run only implicated tests; run the full suite when the work is complete

## Documentation

Consult documentation when you need deeper context on how subsystems work.

### User Docs
`/docs/` - Quarto-based documentation site: https://meridianlabs-ai.github.io/inspect_scout/
- Scanners, transcripts, validation, results, projects, workflows, DB schema

### Design Documents
Architecture and design decisions in `/design/`.

- [Transcript data pipeline](design/data-pipeline.md)
- [Job vs infrastructure exceptions](design/exception_handling.md)
- [Async generator semantics](design/generator-iterator.md)
- [Multi-process concurrency](design/mp.md)
- [Validation data structures](design/validation.md)
- [React Query patterns](src/inspect_scout/_view/frontend/apps/scout/design/react-query.md)
- [Frontend specific testing](src/inspect_scout/_view/frontend/apps/scout/design/front-end-testing.md)

### Guides
Developer workflow guides in `/guides/`.

- [Frontend submodule guide](guides/frontend-submodule.md)

## Python

Directory: `src/inspect_scout/`

### Scripts
| Command | Description |
|---------|-------------|
| `make check` | Run all checks (lint, format, typecheck) |
| `make test` | Run all tests |
| `pytest` | Run all tests |
| `pytest tests/path/to/test.py::test_name -v` | Run single test |
| `ruff format` | Format code |
| `ruff check --fix` | Lint and auto-fix |
| `mypy src examples tests` | Type check |

### Style
- **Formatting**: Follow Google style convention. Use ruff for formatting
- **Imports**: Use isort order (enforced by ruff)
- **Types**: All functions must have type annotations, including in tests.
- **Naming**: Use snake_case for variables, functions, methods; PascalCase for classes
- **Docstrings**: Google-style docstrings required for public APIs
- **Error Handling**: Use appropriate exception types; include context in error messages
- **Testing**: Write tests with pytest; maintain high coverage

### Common Pitfalls
- Use the venv for all Python commands: either reference `.venv/bin/` directly or run `source .venv/bin/activate`
- **Never use `uv sync` or `uv run`**—developers often have local editable installs (e.g., `pip install -e` for inspect_ai) that uv silently removes


## TypeScript

Directory: `src/inspect_scout/_view/frontend/` (run all commands from here)

See the frontend's own [CLAUDE.md](src/inspect_scout/_view/frontend/CLAUDE.md) for full details.

### Setup
```bash
corepack enable  # once
pnpm install
```

### Scripts
| Command | Description |
|---------|-------------|
| `pnpm check` | Run all checks (lint, format, typecheck) via Turborepo |
| `pnpm dev` | Start dev server (user typically has this running—don't start) |
| `pnpm watch` | Watch mode (user typically has this running—don't start) |
| `pnpm build` | Production build |
| `pnpm test` | Run unit/integration tests |
| `pnpm lint` | Lint all packages |
| `pnpm typecheck` | Type-check all packages |
| `pnpm format` | Format code |

### Style
- Strict mode enabled; no `any`, no type assertions
- ESLint + Prettier

### Common Pitfalls
- Use pnpm, not npm—this project uses pnpm exclusively
- Hook tests don't need JSX—use `.test.ts` not `.test.tsx`; see `useMapAsyncData.test.ts`
- Run `pnpm build` before committing (not just `pnpm check`)—we ship the built .js code


## Type Sharing (Python → TypeScript)

Pipeline: Pydantic models → openapi.json → generated.ts

After Python API changes:
1. `.venv/bin/python scripts/export_openapi_schema.py`
2. `pnpm build` (regenerates types)
3. Commit both `openapi.json` and `src/types/generated.ts`

Manual: `pnpm types:generate`

CI validates sync.

