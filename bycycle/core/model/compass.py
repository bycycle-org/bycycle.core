from bycycle.core.util import swapKeysAndValues


directions_ftoa = {
    'north': 'n',
    'south': 's',
    'east': 'e',
    'west': 'w',
    'northeast': 'ne',
    'northwest': 'nw',
    'southeast': 'se',
    'southwest': 'sw',
}
directions_atof = swapKeysAndValues(directions_ftoa)


directions_dtoa = {
    '0': 'n',
    '180': 's',
    '90': 'e',
    '270': 'w',
    '45': 'ne',
    '315': 'nw',
    '135': 'se',
    '225': 'sw',
}
directions_atod = swapKeysAndValues(directions_dtoa)


suffixes_ftoa = {
    'northbound': 'nb',
    'southhbound': 'sb',
    'eastbound': 'eb',
    'westbound': 'wb',
}
suffixes_atof = swapKeysAndValues(suffixes_ftoa)
