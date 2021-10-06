.PHONY = init
init: .venv
	./.venv/bin/runcommand init

.venv:
	python -m venv .venv
	poetry install
