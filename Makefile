.PHONY: ruff
ruff:
	ruff check --fix
	ruff format

.PHONY: mypy
mypy:
	mypy src examples tests

.PHONY: suppressions-check
suppressions-check:
	python3 scripts/check_suppressions.py

.PHONY: suppressions-update
suppressions-update:
	python3 scripts/check_suppressions.py --update

.PHONY: check
check: ruff mypy suppressions-check

.PHONY: test
test:
	pytest
