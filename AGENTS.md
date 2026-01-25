# AGENTS.md

## Repository Structure
- **Python package** (`src/inspect_scout/`) - Core library for analyzing LLM evaluation transcripts. Provides a CLI, programmatic API, and FastAPI server. Handles transcript databases, scanners, validation, and results.
- **React frontend** (`src/inspect_scout/_view/www/`) - Web UI for viewing scan results, exploring transcripts, and managing projects.

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

- [data-pipeline.md](design/data-pipeline.md) - Transcript data pipeline
- [exception_handling.md](design/exception_handling.md) - Job vs infrastructure exceptions
- [generator-iterator.md](design/generator-iterator.md) - Async generator semantics
- [mp.md](design/mp.md) - Multi-process concurrency
- [validation.md](design/validation.md) - Validation data structures
- [TODO.md](design/TODO.md) - Future work

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

Directory: `src/inspect_scout/_view/www/` (run all commands from here)

### Setup
```bash
corepack enable  # once
pnpm install
```

### Scripts
| Command | Description |
|---------|-------------|
| `pnpm check` | Run all checks (lint, format, typecheck) |
| `pnpm dev` | Start dev server (user typically has this running—don't start) |
| `pnpm watch` | Watch mode (user typically has this running—don't start) |
| `pnpm build` | Production build |
| `pnpm test` | Run tests |
| `pnpm lint` | Lint code |
| `pnpm lint:fix` | Lint and auto-fix |
| `pnpm format` | Format code |
| `pnpm typecheck` | Type check |

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

