#!/usr/bin/env python
###############################################################################
# $Id: shp2pgsql.py 187 2006-08-16 01:26:11Z bycycle $
# Created 2007-05-08.
#
# Data integration front end script.
#
# Copyright (C) 2006-2008 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""
Usage::

    shp2pgsql.py [various options, see below]

Example::

    shp2pgsql.py --region portlandor --source pirate --layer str06oct -n
    
    In this example, --region is the region "key" matching the region's
    Python module name and ``slug`` in the public.regions database table.
    
    --source is the name of a directory in ${HOME}/byCycleData/portlandor. In
    this case, on my machine, it refers to the directory
    /home/bycycle/byCycleData/portlandor/pirate. 
    
    [Note that, for now, ${HOME}/byCycleData can't be changed from the command
    line. It can be changed by creating an Integrator and setting its
    ``base_data_path`` attribute. It might also be possible to set --source as
    an absolute path, but I haven't tried this.]

    --layer is the base name of a shapefile and its associated DBF and other
    files. In this example, the pirate directory contains the files
    str06oct.shp, str06oct.dbf, etc.

    -n (short for --no-prompt) indicates that we want to run all of the data
    integration actions without being prompted. In normal use, this will
    probably be the default.

Options::

    --region | -r <region key>
        The unique "region key" for a region. It should match the region's
        Python module name. REQUIRED.

    --source | -d <data source name>
        The data source. This is a directory containing shapefiles. For now,
        it is always relative to ${HOME}/byCycleData. REQUIRED.
        
    --layer | -l <layer name>    
        The data layer. This is the base name for a shapefile and its related
        files. For example, if the layer name is "str06oct", there will be
        corresponding files named "str06oct.shp", "str06oct.dbf", etc.
        REQUIRED.
        
    --start | -s <index>
        The index (0-based) of the action to start from. Yes, this is clunky
        in that we need to know the index number for an action--a menu system
        should be created. Defaults to 0.
        
    --end | -e <index>
        Like --start but for the last action that should be run. Defaults to
        one less than the number of actions.
        
    --no-prompt | -n
        Run the actions from --start to --end without prompting. The default
        is to prompt for every action.
        
    --only | -o <index>
        Do just the action indicated by ``index``, without prompting. By 
        default, this isn't used.
    
    If no args are supplied, the default is to prompt for all actions.

    If either of --start or --end is present, the -only option must not be
    present.

    If --only is present, --no-prompt is implied.

"""
import sys, getopt


def main(argv):    
    # Get command line options
    opts = getOpts(sys.argv[1:])

    region = opts.pop('region')
    source = opts.pop('source')
    layer = opts.pop('layer')
    no_prompt = bool(opts.get('no_prompt', opts.get('only', False)))
    
    imp_path = 'byCycle.model.%s.data.integrator' % region
    integrator_module = __import__(imp_path, locals(), globals(), [''])

    integrator = integrator_module.Integrator(region, source, layer, **opts)

    if opts['end'] is None:
        opts['end'] = len(integrator.actions) - 1

    integrator.run(**opts)


def getOpts(argv):
    """Parse the opts from ``argv`` and return them as a ``dict``."""
    required_opts = 'region', 'source', 'layer'
    opts = {
        'start': 0,
        'end': None,
        'no_prompt': False,
        'only': None,
        }
    # Parse args
    try:
        short_opts = 'r:d:l:s:e:no:h'
        long_opts = ['region=', 'source=', 'layer=', 'start=', 'end=',
                     'no-prompt', 'only=', 'help']
        cl_opts, args = getopt.gnu_getopt(argv, short_opts, long_opts)
    except getopt.GetoptError, e:
        usage()
        die(2, str(e))
    start_or_end_specified = False
    # See what args were given and put them in the args dict
    for opt, val in cl_opts:
        if opt not in ('--region', '-r',
                       '--source', '-d',
                       '--layer', '-l',
                       '--no-prompt', '-n',
                       '--help', '-h'):
            try:
                val = int(val)
            except ValueError:
                die(2, '%s value must be an integer.' % opt)
        if opt in ('--region', '-r'):
            opts['region'] = val
        elif opt in ('--source', '-d'):
            opts['source'] = val
        elif opt in ('--layer', '-l'):
            opts['layer'] = val
        elif opt in ('--start', '-s'):
            start_or_end_specified = True
            opts['start'] = val
        elif opt in ('--end', '-e'):
            start_or_end_specified = True
            opts['end'] = val
        elif opt in ('--no-prompt', '-n'):
            opts['no_prompt'] = True
        elif opt in ('--only', '-o'):
            opts['only'] = val
        elif opt in ('--help', '-h'):
            usage()
            sys.exit()
        else:
            usage()
            die(1, 'Unknown option: ``%s``' % opt)

    required_missing = [o for o in required_opts if o not in opts]
    if required_missing:
        msg = 'Required options missing: %s' % ', '.join(required_missing)
        usage()
        die(2, msg)

    if opts['only'] is not None:
        if start_or_end_specified:
            usage()
            die(3, '--only must be the *only* argument or not specified.')
        else:
            opts['no_prompt'] = True

    return opts

def die(code=1, msg=''):
    print 'ERROR: %s' % msg
    sys.exit(code)

def usage(msg=''):
    if msg:
        print '\n%s' % msg
    print __doc__

if __name__ == '__main__':
    main(sys.argv)
