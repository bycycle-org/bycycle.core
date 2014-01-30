#!/usr/bin/env python
"""Command-line interface to the byCycle library."""
import importlib
import sys

import bycycle.core.services
from bycycle.core.model import regions
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
        service_module = importlib.import_module(
            '.' + service, 'bycycle.core.services')

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
    timer.start()
    service = service_module.Service(region=region)
    response = service.query(q)
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
