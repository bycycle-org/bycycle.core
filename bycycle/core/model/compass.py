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


suffixes_ftoa = {
    'northbound': 'nb',
    'southhbound': 'sb',
    'eastbound': 'eb',
    'westbound': 'wb',
}
suffixes_atof = {v: k for k, v in suffixes_ftoa.items()}
