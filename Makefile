.PHONY: ruff
ruff:
	ruff check --fix
	ruff format

.PHONY: mypy
mypy:
	mypy src examples tests

.PHONY: check
check: ruff mypy

.PHONY: test
test:
	pytest
