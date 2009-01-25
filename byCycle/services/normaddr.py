################################################################################
# $Id$
# Created ???.
#
# Address Normalization service.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
"""
Provides address normalization via the `query` method of the `Service` class.

Address normalization is the process of parsing a free form string supplied by
a user and determining the parts of the address, such as the street direction
(N, SE, etc), street name and type (St, Rd, etc), and city, state, and zip.

The service recognizes these types of addresses:

- Postal (e.g., 633 N Alberta, Portland, OR)
- Intersection (e.g., Alberta & Kerby)
- Point (e.g., x=-123, y=45)
- Node (i.e., node ID)
- Edge (i.e., number + edge ID).

"""
import re
from byCycle import services
from byCycle.services.exceptions import ByCycleError, InputError
from byCycle.model import address, regions, states, sttypes, compass
from byCycle.model.entities import StreetName, Place


# RE to check to see if a string has at least one word char
re_word_plus = re.compile(r'\w+')

directions_ftoa = compass.directions_ftoa
directions_atof = compass.directions_atof
suffixes_ftoa = compass.suffixes_ftoa
suffixes_atof = compass.suffixes_atof
sttypes_ftoa = sttypes.street_types_ftoa
sttypes_atof = sttypes.street_types_atof
states_ftoa = states.states_ftoa
states_atof = states.states_atof

no_address_msg = 'Please enter an address.'
no_region_msg = 'Please select a region.'


class Service(services.Service):
    """Address Normalization Service."""

    name = 'address'

    def __init__(self, region=None):
        """

        ``region`` `Region` | `string`
            `Region` or region key

        """
        services.Service.__init__(self, region=region)

    def query(self, q):
        """Get a normalized address for the input address.

        Try to parse the parts of the address in ``q``. Return an `Address` of
        the appropriate type for ``q`` or raises a `ValueError` if the address
        isn't "understood".

        ``q`` `string`
            An address to be normalized in the given ``region``.

        return `Address`
            `Address` object with normalized attributes

        raise `InputError`
            - ``q`` is empty
            - No region supplied for edge or node type address
            - Region not supplied & can't be determined for other address types
            - ``q`` cannot be parsed

        """
        original_q = q
        q = q.strip().lower()
        if not q:
            raise InputError(no_address_msg)

        try:
            q, addr = q.split(';')
        except ValueError:
            addr = q
            trying_id = False
        else:
            trying_id = True

        lAddr = addr.split('-')

        # Edge?
        try:
            num = int(lAddr[0])
            network_id = int(lAddr[1])
        except (IndexError, ValueError):
            pass
        else:
            if not self.region:
                try:
                    self.region = lAddr[2]
                except IndexError:
                    raise InputError(no_region_msg)
            return address.EdgeAddress(num, network_id, self.region.slug)

        # Node?
        try:
            network_id = int(lAddr[0])
        except (IndexError, ValueError):
            pass
        else:
            if not self.region:
                try:
                    self.region = lAddr[1]
                except IndexError:
                    raise InputError(no_region_msg)
            return address.NodeAddress(network_id, self.region.slug)

        # Intersection?
        try:
            street_name1, street_name2 = self._getCrossStreets(q)
        except ValueError:
            pass
        else:
            # parse streets and return IntersectionAddress
            parse_info1 = self._parse(street_name1)
            stname1, sttype1, place1, city_region1, zip_region1 = parse_info1
            parse_info2 = self._parse(street_name2)
            stname2, sttype2, place2, city_region2, zip_region2 = parse_info2
            try:
                self._checkAndMaybeSetRegion(original_q, city_region1,
                                             zip_region1)
            except InputError:
                self._checkAndMaybeSetRegion(original_q, city_region2,
                                             zip_region2)
            self._adjustName(stname1, sttype1)
            self._adjustName(stname2, sttype2)
            return address.IntersectionAddress(
                stname1, place1, stname2, place2
            )

        # Postal Address?
        try:
            number, street_name = self._getNumberAndStreetName(q)
        except ValueError:
            pass
        else:
            # parse street and return PostalAddress
            parse_info = self._parse(street_name)
            stname, sttype, place, city_region, zip_region = parse_info
            self._checkAndMaybeSetRegion(original_q, city_region, zip_region)
            self._adjustName(stname, sttype)
            return address.PostalAddress(number, stname, place)

        # Point?
        try:
            point_addr = address.PointAddress(q)
        except ValueError:
            pass
        else:
            if not self.region:
                # TODO: Determine which region point is within or closest to
                raise InputError(no_region_msg)
            return point_addr

        if trying_id:
            return self.query(q)

        # Raise an exception if we get here: address is unnormalizeable
        raise InputError(
            'We could not understand the address you entered, "%s".' %
            str(original_q),
            """\
The trip planner currently only understands street addresses such as "123 Main St" or "1st & Main". (City, state, and zip code are all optional.)

In particular, the trip planner doesn't know about points of interest such as parks, libraries, or airports.

It also doesn't recognize cities, states, and/or zip codes by themselves, so if you type in "Portland, OR" you will get this error.

Another possible reason is that you entered a street name without a number. For example, if you entered just "Main St," this error basically is asking "Where on Main St?" You have to give the building number ("123 Main St") or use cross streets ("1st and Main").
"""
        )

    def _parse(self, addr):
        """Parse input address string.

        ``addr`` `string` -- A street name & place with no number (e.g., Main
        St, Portland, OR). It *must* contain at least the name part of a
        street name. It must *not* contain a house number. It *can* contain a
        city & state OR zip code OR both.

        return
            `StreetName` -- Prefix, name, type, and suffix
            `string` -- Full street type (i.e., the unabbreviated version of
                        the street type), iff found, or None
            `Place` -- City name (but not city ID!), state ID (two letter
                       state abbreviation), state name, and zip code
            `string` -- Region key determined from city and state
            `string` -- Region key determined from zip code

        TODO: For some cases, we could actually fill in more info. For
        example, if a zip code is given, we can fill in at least the state and
        possibly the city (if there happens to be just one city in the zip
        code). This could help out a lot with geocoding.

        """
        addr = addr.replace(',', ' ')
        addr = addr.replace('.', '')
        tokens = addr.lower().split()
        name = []
        street_name = StreetName()
        full_sttype = None
        place = Place()
        city_region_key, zip_region_key = None, None

        try:
            # If there's only one token, it must be the name
            if len(tokens) == 1:
                raise IndexError

            # -- Front to back

            # prefix
            prefix = tokens[0]
            if (prefix in directions_atof or prefix in directions_ftoa):
                if prefix in directions_ftoa:
                    prefix = directions_ftoa[prefix]
                street_name.prefix = prefix
                del tokens[0]

            # name
            # Name must have at least one word
            name.append(tokens[0])
            del tokens[0]

            # -- Back to front

            # zip code
            zip_region_key = None
            zip_code = tokens[-1]
            try:
                zip_code = int(zip_code)
            except ValueError:
                pass
            else:
                if 10000 <= zip_code <= 99999:
                    del tokens[-1]
                    if zip_code in regions.zip_codes:
                        if not self.region:
                            zip_region_key = regions.zip_codes[zip_code]
                        place.zip_code = zip_code

            # state
            for i in (-1, -2, -3, -4):
                state_code = ' '.join(tokens[i:])
                if (state_code in states_atof or state_code in states_ftoa):
                    if state_code in states_ftoa:
                        state = state_code
                        state_code = states_ftoa[state_code]
                    else:
                        state = states_atof[state_code]
                    place.state_code = state_code
                    place.state_name = state
                    del tokens[i:]
                    break

            # Get cities for state if state; else use list of all cities
            try:
                cities = regions.states_cities[place.state_code]
            except KeyError:
                cities = regions.cities

            # city
            city_region_key = None
            for i in (-1, -2, -3, -4):
                city = ' '.join(tokens[i:])
                if city in cities:
                    if not self.region:
                        _region = cities[city]
                        if isinstance(_region, list):
                            if len(_region) == 1:
                                city_region_key = _region[0]
                        else:
                            city_region_key = _region
                    place.city_name = city
                    del tokens[i:]
                    break

            # suffix
            suffix = tokens[-1]
            if (suffix in directions_atof or suffix in suffixes_atof or
                suffix in directions_ftoa or suffix in suffixes_ftoa):
                if suffix in directions_ftoa:
                    suffix = directions_ftoa[suffix]
                elif suffix in suffixes_ftoa:
                    suffix = suffixes_ftoa[suffix]
                street_name.suffix = suffix
                del tokens[-1]

            # street type
            sttype = tokens[-1]
            if (sttype in sttypes_atof or sttype in sttypes_ftoa):
                if sttype in sttypes_atof:
                    # Make sure we have the official abbreviation
                    sttype = sttypes_atof[sttype]
                    sttype = sttypes_ftoa[sttype]
                elif sttype in sttypes_ftoa:
                    full_sttype = sttype
                    sttype = sttypes_ftoa[sttype]
                street_name.sttype = sttype
                del tokens[-1]
        except IndexError:
            pass
        street_name.name = ' '.join(name + tokens)
        return street_name, full_sttype, place, city_region_key, zip_region_key

    def _checkAndMaybeSetRegion(self, q, city_region_key, zip_region_key):
        if not self.region:
            if city_region_key:
                # Prefer city/state region
                self.region = city_region_key
            elif zip_region_key:
                # No city/state region found; try zip code region
                self.region = zip_region_key
            else:
                # By here, we should have figured out the region; if not, fail.
                raise InputError('Please enter a city and state -OR- a zip '
                                 'code -OR- set your region for address '
                                 '"%s"' % q)

    def _adjustName(self, street_name, sttype):
        """Adjust ``street_name``'s name.

        ``street_name`` `StreetName`
        ``sttype`` `string` -- Original street type found by `_parse`

        First, if the name is a number, add a suffix: 1 => 1st, 11 => 11th,
        etc. Then, if the name can't be found in the DB and the street type
        entered was not abbreviated, see if we can find the name+type in the
        in the name column of the street names table. If so, use the name+type
        as the name and unset the street type.

        Note: self.region must be set before calling this.

        """
        name = street_name.name
        num_name = self._appendSuffixToNumberStreetName(name)
        StreetName = self.region.module.StreetName
        if sttype in sttypes_ftoa:
            # If a full street type was entered...
            # E.g., street name is 'johnson' and street type is 'creek'
            c = StreetName.c
            count1 = StreetName.count((c.name == num_name) &
                                      (c.sttype == sttype))
            if not count1:
                # ...and there is no street in the DB with the name & type...
                # i.e., there's no street named 'johnson' with type 'creek'
                name_type = '%s %s' % (name, sttype)
                count2 = StreetName.count(c.name == name_type)
                if count2:
                    # ...but there is one with that looks like 'name type'...
                    # i.e., there's a street named 'johnson creek' with type x
                    # ...use the name with type appended as the street's name...
                    # i.e., use 'johnson creek' as the name
                    name = name_type
                    # ...and assume there was no street type entered.
                    street_name.sttype = None
        else:
            name = num_name
        street_name.name = name

    def _appendSuffixToNumberStreetName(self, name):
        """Add suffix to number street ``name`` if needed (e.g. 10 => 10th).

        ``name`` `string`

        return `string` -- If ``name`` is not a number, it's just returned as
        is; otherwise, return ``name`` with suffix appended.

        """
        try:
            int(name)
        except ValueError:
            pass
        else:
            last_char = name[-1]
            try:
                last_two_chars = name[-2:]
            except IndexError:
                last_two_chars = ''
            if last_char == '1' and last_two_chars != '11':
                name += 'st'
            elif last_char == '2' and last_two_chars != '12':
                name += 'nd'
            elif last_char == '3' and last_two_chars != '13':
                name += 'rd'
            else:
                name += 'th'
        return name

    def _getCrossStreets(self, sAddr):
        """Try to extract two cross streets from the input address.

        Try splitting ``addr`` on 'and', 'at', '&', '@', '+', '/', or '\'.
        'and' &and 'at' must have whitespace on both sides. All must have at
        least one word character on both sides.

        ``addr`` `string` -- An intersection-style address with a pair of
        cross streets separated by one of the symbols listed above.

        """
        sRe = r'\s+and\s+|\s+at\s+|\s*[&@\+/\\\|]\s*'
        oRe = re.compile(sRe, re.I)
        streets = re.split(oRe, sAddr)
        if (len(streets) > 1 and
            re.match(re_word_plus, streets[0]) and
            re.match(re_word_plus, streets[1])):
            return streets
        err = '"%s" could not be parsed as an intersection address' % sAddr
        raise ValueError(err)

    def _getNumberAndStreetName(self, sAddr):
        """Try to extract a house number and street name from input address."""
        tokens = sAddr.split()
        if len(tokens) > 1:
            num = tokens[0]
            try:
                # Is num an int (house number)?
                num = int(num)
            except ValueError:
                # No.
                pass
            else:
                # num is an int; is street name a string with at least one
                # word char?
                street_name = ' '.join(tokens[1:])
                if re.match(re_word_plus, street_name):
                    # Yes.
                    return num, street_name
        err = '"%s" could not be parsed as a postal address' % sAddr
        raise ValueError(err)
