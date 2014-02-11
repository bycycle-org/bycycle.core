"""Create adjacency matrix for a region or regions.

The matrix for one or more regions can be created by specifying the
region or regions like so::

    bycycle-matrix portlandor

The matrices for all regions can be created by using the special value
"all"::

    bycycle-matrix all

"""
import argparse
import sys

from bycycle.core.model import db, Region


help_text = __doc__


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=help_text,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('regions', nargs='+')

    if argv is not None:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    db.init()
    session = db.make_session()

    if 'all' in args.regions:
        print('Creating all matrices...')
        regions = session.query(Region).all()
    else:
        regions = []
        for slug in args.regions:
            q = session.query(Region).filter_by(slug=slug)
            region = q.first()
            if region is None:
                sys.stderr.write('Unknown region {0}'.format(slug))
                sys.exit(1)
            regions.append(region)
    for region in regions:
        print('Creating matrix for {0.title}...'.format(region))
        region.createAdjacencyMatrix()
