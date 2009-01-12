###############################################################################
# $Id$
# Created ???
#
# A few miscellaneous utility functions.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
def getMostFrequentInList(the_list):
    """Get the list item that occurs most often."""
    cnt = {}
    the_list = [i for i in the_list if i]
    for i in the_list:
        cnt[i]=cnt.get(i, 0) + 1
    C = [None] + sorted(cnt.keys(), key=cnt.get)
    return C[-1]


def joinAttrs(attrs, join_string=' '):
    """Join the values in attrs, leaving out empty values."""
    if isinstance(attrs, dict):
        attrs = attrs.values()
    return join_string.join([str(a) for a in attrs if a])


def swapKeysAndValues(old_dict):
    """Make a new dict with keys and values in given dict swapped.

    In other words, make a new dict that has the keys of the old dict as the
    values and the respective values of the old dict as the keys to those
    values.

    """
    new_dict = {}
    for k in old_dict:
        new_dict[old_dict[k]] = k
    return new_dict
