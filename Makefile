.PHONY: ruff
ruff:
	ruff check --fix
	ruff format

.PHONY: mypy
mypy:
	mypy src examples tests

.PHONY: carveouts
carveouts:
	python3 scripts/check_config_carveouts.py

.PHONY: check
check: ruff mypy carveouts

.PHONY: test
test:
	pytest
