#!/usr/bin/env python2.5
"""Create adjacency matrix for region given as first arg on command line."""
import sys
from byCycle.model import Region

no_region_msg = ('Specify a region name. Use "all" to create matrices for '
                 'all regions.')

def die(error_msg):
    sys.stderr.write(str(error_msg) + '\n')
    sys.exit(1)

def make_matrix_for_region(region):
    print 'Creating matrix for %s...' % region.title
    region.createAdjacencyMatrix()

if __name__ == '__main__':
    region_slugs = sys.argv[1:] if len(sys.argv) > 1 else die(no_region_msg)
    if len(region_slugs) == 1 and region_slugs[0] == 'all':
        print 'Creating all matrices...'
        regions = Region.select()
        for r in regions:
            make_matrix_for_region(r)
    else:
        for slug in region_slugs:
            r = Region.get_by(slug=slug)
            if r is None:
                die('Unknown region "%s"' % slug)
            make_matrix_for_region(r)
