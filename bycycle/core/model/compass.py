############################################################################### $Id$
# Created 2005-??-??.
#
# Database Abstraction Layer.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from byCycle.util import swapKeysAndValues


directions_ftoa = {
    'north'     : 'n',
    'south'     : 's',
    'east'      : 'e',
    'west'      : 'w',
    'northeast' : 'ne',
    'northwest' : 'nw',
    'southeast' : 'se',
    'southwest' : 'sw',
}
directions_atof = swapKeysAndValues(directions_ftoa)


directions_dtoa = {
    '0'   : 'n',
    '180' : 's',
    '90'  : 'e',
    '270' : 'w',
    '45'  : 'ne',
    '315' : 'nw',
    '135' : 'se',
    '225' : 'sw',
}
directions_atod = swapKeysAndValues(directions_dtoa)


suffixes_ftoa = {
    'northbound'  : 'nb',
    'southhbound' : 'sb',
    'eastbound'   : 'eb',
    'westbound'   : 'wb',
}
suffixes_atof = swapKeysAndValues(suffixes_ftoa)
