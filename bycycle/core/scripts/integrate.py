"""Import regional data into database.

Example::

    bycycle-integrate -r portlandor -d pirate -l str06oct -n

    -r is the region key matching the region's Python module name and
    slug in the public.regions database table.

    -d is the name of a directory in ${HOME}/byCycleData/portlandor.

    For now, ${HOME}/byCycleData can't be changed from the command line.
    It can be changed by creating a `model.data.Integrator` subclass and
    setting its `base_data_path` attribute.

    -l is the base name of a shapefile and its associated DBF and other
    files. In this example, the pirate directory contains the files
    str06oct.shp, str06oct.dbf, etc.

    -n indicates that we want to run all of the data integration actions
    without being prompted. In normal use, this will probably be the
    default.

Options::

    --region | -r REGION
        The unique key for a region. It should match the region's Python
        module name. REQUIRED.

    --source | -d SOURCE
        The data source. This is a directory containing shapefiles. For
        now, it is always relative to ${HOME}/byCycleData. REQUIRED.

    --layer | -l LAYER
        The data layer. This is the base name for a shapefile and its
        related files. For example, if the layer name is "str06oct",
        there will be corresponding files named str06oct.shp,
        str06oct.dbf, etc. REQUIRED.

    --start | -s START
        The index (0-based) of the action to start from. Yes, this is
        clunky in that we need to know the index number for an action--a
        menu system should be created. Defaults to 0.

    --end | -e END
        Like --start but for the last action that should be run.
        Defaults to one less than the number of actions.

    --only | -o INDEX
        Do just the action indicated by INDEX, without prompting.
        --start and --end should not be specified if this is. Implies
        --no-prompt.

    --no-prompt | -n
        Run the actions from --start to --end without prompting. The
        default is to prompt for every action.

    If none of --start, --end, or --only are specified, the default is
    to prompt for all actions.

"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-r', '--region', required=True)
    parser.add_argument('-d', '--source', required=True)
    parser.add_argument('-l', '--layer', required=True)
    parser.add_argument('-n', '--no-prompt', action='store_true', default=False)
    parser.add_argument('-s', '--start', type=int, default=None)
    parser.add_argument('-e', '--end', type=int, default=None)
    parser.add_argument('-o', '--only', type=int, default=None)

    if argv is not None:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    args.no_prompt = args.no_prompt or (args.only is not None)

    start, end, only = args.start, args.end, args.only
    if None in (start, end) and only is not None:
        raise parser.error(
            '--only not allowed with --start or --end')

    imp_path = 'bycycle.core.model.{0.region}.data.integrator'.format(args)
    integrator_module = __import__(imp_path, locals(), globals(), [''])

    integrator = integrator_module.Integrator(
        args.region, args.source, args.layer, args.no_prompt)

    integrator.run(
        start=args.start, end=args.end, only=args.only,
        no_prompt=args.no_prompt)
