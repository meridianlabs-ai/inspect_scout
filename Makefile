.PHONY: mypy
mypy:
	mypy src examples

.PHONY: check
check: mypy
	ruff check --fix
	ruff format

.PHONY: test
test:
	pytest
