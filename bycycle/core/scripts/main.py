import argparse
import re
import time

from tangled.util import load_object

from bycycle.core import db


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('service')
    parser.add_argument('q')
    args = parser.parse_args(argv)

    module_name = 'bycycle.core.service.{}'.format(args.service)
    service_factory = load_object(module_name, 'Service')

    q = args.q

    if args.service == 'route':
        q = re.split('\s+to\s+', q, re.I)
        if len(q) < 2:
            parser.error('Route must be specified as "A to B"')

    db.init()
    session = db.make_session()
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
