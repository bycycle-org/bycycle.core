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
directions_atof = {v: k for k, v in directions_ftoa.items()}


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
directions_atod = {v: k for k, v in directions_dtoa.items()}


suffixes_ftoa = {
    'northbound': 'nb',
    'southhbound': 'sb',
    'eastbound': 'eb',
    'westbound': 'wb',
}
suffixes_atof = {v: k for k, v in suffixes_ftoa.items()}
