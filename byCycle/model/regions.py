###############################################################################
# $Id$
# Created 2006-08-??.
#
# Info on regions.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Info on regions.

TODO: This should stored in the database.

"""
from byCycle.model.entities import Region


unknown_region = None
portlandor = 'portlandor'
milwaukeewi = 'milwaukeewi'
pittsburghpa = 'pittsburghpa'
seattlewa = 'seattlewa'

region_keys = (portlandor, milwaukeewi, pittsburghpa, seattlewa)
regions = dict([(r, 1) for r in region_keys])

states = ('or', 'pa', 'wa', 'wi')
states_cities = dict([(s, {}) for s in states])
states_cities['pa']['pittsburgh'] = pittsburghpa
states_cities['wa']['vancouver'] = portlandor
states_cities['wa']['seattle'] = seattlewa

portlandor_cities = (
    'columbia', 'washington', 'multnomah', 'portland', 'banks',
    'north plains', 'hillsboro', 'gresham', 'fairview', 'maywood park',
    'forest grove', 'troutdale', 'beaverton', 'wood village', 'cornelius',
    'hood river', 'milwaukie', 'clackamas', 'happy valley', 'tigard', 'gaston',
    'yamhill', 'lake oswego', 'king city', 'sandy', 'johnson city', 'durham',
    'tualitin', 'gladstone', 'west linn', 'rivergrove', 'oregon city',
    'sherwood', 'wilsonville', 'estacada', 'canby', 'barlow', 'molalla',
    'marion'
    )
states_cities['or'].update(dict([(c, portlandor) for c in portlandor_cities]))

milwaukeewi_cities = (
    'bayside', 'brown deer', 'cudahy', 'fox point', 'franklin', 'glendale',
    'greendale', 'greenfield', 'hales corners', 'milwaukee', 'oak creek',
    'river hills', 'saint francis', 'shorewood', 'south milwaukee',
    'wauwatosa', 'west allis', 'west milwaukee', 'whitefish bay'
)
states_cities['wi'].update(dict([(c, milwaukeewi) for c in milwaukeewi_cities]))


# city => list of regions with city
cities = {}
for state in states_cities:
    cities_in_state = states_cities[state]
    for city in cities_in_state:
        region = cities_in_state[city]
        if city in cities:
            cities[city].append(region)
        else:
            cities[city] = [region]


# zip code => region key
zip_codes = {}

portlandor_zip_codes = (
    97002, 97004, 97005, 97006, 97007, 97008, 97009, 97010, 97011, 97013,
    97014, 97015, 97017, 97019, 97022, 97023, 97024, 97027, 97028, 97030,
    97032, 97034, 97035, 97036, 97038, 97042, 97045, 97049, 97055, 97056,
    97060, 97062, 97064, 97067, 97068, 97070, 97071, 97080, 97106, 97109,
    97113, 97116, 97117, 97119, 97123, 97124, 97125, 97132, 97133, 97140,
    97141, 97144, 97201, 97202, 97203, 97204, 97205, 97206, 97209, 97210,
    97211, 97212, 97213, 97214, 97215, 97216, 97217, 97218, 97219, 97220,
    97221, 97222, 97223, 97224, 97225, 97227, 97229, 97230, 97231, 97232,
    97233, 97236, 97239, 97258, 97266, 97267, 97358, 97362, 97375, 97761,
    98660
)
zip_codes.update(dict([(zc, portlandor) for zc in portlandor_zip_codes]))


# region key alias => region key
aliases = ('all',)
region_aliases = dict([(a, 'all') for a in aliases])

aliases = (milwaukeewi, 'mil', 'milwaukee')
region_aliases.update(dict([(a, milwaukeewi) for a in aliases]))

aliases = (portlandor, 'metro', 'pdx', 'portland')
region_aliases.update(dict([(a, portlandor) for a in aliases]))

aliases = (pittsburghpa, 'pgh')
region_aliases.update(dict([(a, pittsburghpa) for a in aliases]))


def getRegionKey(region):
    """Find the proper region key for ``region``.

    ``region``
        A region proper name, alias, or key, or None

    return `string`
        Lowercase region key.
        
    raise ValueError
        ``region`` is not a known region name, alias, or key.

    """
    if region is None:
        return None
    region = (region or '').strip()
    region = ''.join(region.split())
    chars = (',', '.', '-')
    for c in chars:
        region = region.replace(c, '')
    region = region.lower()
    if not region:
        return None
    try:
        region = region_aliases[region]
    except KeyError:
        raise ValueError('Could not determine region key for "%s"' % region)
    return region


def getRegion(region):
    """Get `Region` for ``region``.

    If ``region`` is a `Region` or `None`, just return ``region``; if it's a 
    valid region key, create a new `Region`.

    ``region`` `Region` | `string` | `None`
        Either a `Region` object or a region key. 
    
    return `Region` | None

    raise ValueError
        Region key cannot be determined for ``region``

    """
    if region:
        if isinstance(region, Region):
            _region = region
        else:
            region_key = getRegionKey(region)
            if region_key == 'all':
                _region = None
            else:
                _region = Region.get_by(slug=region_key)
    else:
        _region = None
    return _region
