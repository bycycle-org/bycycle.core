#!/usr/bin/env python
"""Command-line interface to the byCycle library."""
import importlib
import sys

from tangled.util import load_object

from bycycle.core.model import db, regions
from bycycle.core.util import meter


services = {
    'n': 'normaddr',
    'g': 'geocode',
    'r': 'route'
}

errors = []

timer = meter.Timer()


def main(argv):
    checkForErrors()

    try:
        service = argv[1]
    except IndexError:
        addError('No service specified')
    else:
        service = services.get(service, service)
        module_name = 'bycycle.core.services.{}'.format(service)
        service_factory = load_object(module_name, 'Service')

    try:
        q = argv[2]
    except IndexError:
        addError('No query specified')

    checkForErrors()

    if service == 'route':
        if len(q.lower().split(' to ')) < 2:
            addError('Route must be specified as "A to B"')
        else:
            q = q.split(' to ')

    checkForErrors()

    try:
        region = argv[3]
    except IndexError:
        region = ''

    region = regions.getRegionKey(region)
    db.init()
    session = db.make_session()
    timer.start()
    try:
        service = service_factory(session, region=region)
        response = service.query(q)
    except Exception:
        session.rollback()
        raise
    else:
        session.close()
        print(response)
    print('%.2f seconds' % timer.stop())


def addError(e):
    errors.append(e)


def checkForErrors():
    if errors:
        usage(errors)
        sys.exit(2)


def usage(msgs=[]):
    print(
        'Usage: bycycle.py '
        '<normaddr|n|geocode|g|route|r> '
        '<query|address|intersection> '
        '[<region>]')
    for msg in msgs:
        print('- %s' % msg)


if __name__ == '__main__':
    main(sys.argv)
