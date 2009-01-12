#!/usr/bin/env python
# $Id$
# Created: 2006-09-26

"""
Command-line interface to the byCycle library.

"""
import os
def __getbyCycleImportPath(level):
    """Get path to dir containing the byCycle package this module is part of.
    
    ``level`` `int`
        How many levels up the dir containing the package is.
        
    TODO: In Python 2.5 I think this just becomes 
          "from ...byCycle.model import <stuff>" or maybe
          "from ..model import <stuff>"
    
    """
    path = os.path.abspath(__file__)
    opd = os.path.dirname
    for i in range(level):
        path = opd(path)
    return path

import sys
sys.path.insert(0, __getbyCycleImportPath(3))
from byCycle.model import regions
from byCycle.util import meter


import_path = 'byCycle.services.%s'

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
        if service in services:
            service = services[service]
        try:
            service_module = __import__(import_path % service,
                                        globals(), locals(), [''])
        except ImportError:
            raise
            addError('Unknown service "%s"' % service)
        
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
    print response
    print '%.2f seconds' % timer.stop()


def addError(e):
    errors.append(e)


def checkForErrors():
    if errors:
        usage(errors)
        sys.exit(2)

        
def usage(msgs=[]):
    print 'Usage: bycycle.py ' \
          '<normaddr|n|geocode|g|route|r> ' \
          '<query|address|intersection> ' \
          '[<region>]'
    for msg in msgs:
        print '- %s' % msg


if __name__ == '__main__':
    main(sys.argv)

