import re
import sys
import time

from runcommands import command
from runcommands.util import abort
from tangled.util import load_object

from bycycle.core import db


@command(choices={'service': ('lookup', 'route')})
def bycycle(config, service, q):
    """Run a bycycle service"""
    module_name = 'bycycle.core.service.{service}'.format(service=service)
    service_factory = load_object(module_name, 'Service')

    if service == 'route':
        q = re.split('\s+to\s+', q, re.I)
        if len(q) < 2:
            abort(1, 'Route must be specified as "A to B"')

    _, session_factory = db.init()
    session = session_factory()

    start_time = time.time()
    try:
        service = service_factory(session)
        response = service.query(q)
    except Exception:
        session.rollback()
        raise
    else:
        session.close()
        print(response)
    print('{:.2f} seconds'.format(time.time() - start_time))


if __name__ == '__main__':
    sys.exit(bycycle.console_script())
