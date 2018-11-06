import re
import sys
import time

from runcommands import arg, command
from runcommands.util import abort
from tangled.util import load_object

from bycycle.core.model import get_engine, get_session_factory


@command
def bycycle(service: arg(choices=('lookup', 'route')), q):
    """Run a byCycle service."""
    module_name = 'bycycle.core.service.{service}'.format(service=service)
    service_factory = load_object(module_name, 'Service')

    if service == 'route':
        q = re.split('\s+to\s+', q, re.I)
        if len(q) < 2:
            abort(1, 'Route must be specified as "A to B"')

    engine = get_engine()
    session_factory = get_session_factory(engine)
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
