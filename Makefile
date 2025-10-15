.PHONY: mypy
mypy:
	mypy src

.PHONY: check
check: mypy
	ruff check --fix
	ruff format

.PHONY: test
test:
	pytest
