.PHONY: check
check:
	uv tool run ruff check --fix
	uv tool run ruff format

.PHONY: test
test:
	uv tool run pytest
