init:
	poetry install
	./.venv/bin/runcommand init

sdist: clean clean-dist
	./.venv/bin/poetry build

clean: clean-dist clean-pycache

clean-all: clean-build clean-dist clean-pycache clean-venv

clean-build:
	rm -frv build

clean-dist:
	rm -frv dist

clean-pycache:
	find . -type d -name __pycache__ | xargs rm -rf

clean-venv:
	rm -frv .venv

.PHONY = init sdist clean clean-all clean-build clean-dist clean-pycache clean-venv
