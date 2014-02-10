all: build

build:
	@buildout

test:
	@test -f ./bin/python || make
	@./bin/tangled test

sdist: clean build
	@./bin/python setup.py sdist

clean-buildout:
	@rm -vrf .installed.cfg bin develop-eggs parts

clean-dist:
	@rm -vrf build dist *.egg-info

clean-pycache:
	@echo "Removing __pycache__ directories"
	@find . -type d -name __pycache__ | xargs rm -rf

clean: clean-buildout clean-dist clean-pycache
