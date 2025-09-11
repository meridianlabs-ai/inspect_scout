.PHONY: check
check:
	uv run ruff check --fix
	uv run ruff format
	uv run pyright
	uv run ty check

.PHONY: test
test:
	uv tool run pytest
