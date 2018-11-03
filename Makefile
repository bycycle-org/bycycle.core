venv ?= .venv

init: $(venv)
	$(venv)/bin/pip install runcommands
	$(venv)/bin/pip install -r requirements.txt
	$(venv)/bin/runcommand init

$(venv):
	python3 -m venv $(venv)

sdist: clean clean-dist
	$(venv)/bin/python setup.py sdist

clean: clean-dist clean-pycache

clean-all: clean-build clean-dist clean-pycache clean-venv

clean-build:
	rm -frv build

clean-dist:
	rm -frv dist

clean-pycache:
	find . -type d -name __pycache__ | xargs rm -rf

clean-venv:
	rm -frv $(venv)

.PHONY = init install sdist clean clean-all clean-build clean-dist clean-pycache clean-venv
