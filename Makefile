venv ?= .env

init: $(venv)
	$(venv)/bin/pip install runcommands
	$(venv)/bin/pip install -r requirements.txt
	$(venv)/bin/runcommand init

$(venv):
	virtualenv -p python3 $(venv)

sdist: clean clean-dist
	$(venv)/bin/python setup.py sdist

test:
	$(venv)/bin/tangled test

clean: clean-dist clean-pycache

clean-all: clean clean-venv

clean-dist:
	rm -frv dist

clean-pycache:
	find . -type d -name __pycache__ | xargs rm -rf

clean-venv:
	rm -frv $(venv)

.PHONY = init install sdist test clean clean-all clean-dist clean-pycache clean-venv
