.PHONY: check
check:
	ruff check --fix
	ruff format
	mypy src

.PHONY: test
test:
	run pytest
