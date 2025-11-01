.PHONY: mypy
mypy:
	mypy src examples tests

.PHONY: check
check: mypy
	ruff check --fix
	ruff format

.PHONY: test
test:
	pytest
