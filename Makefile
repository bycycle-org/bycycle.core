.PHONY = init
init: .venv
	./.venv/bin/runcommand init

.venv:
	poetry install
