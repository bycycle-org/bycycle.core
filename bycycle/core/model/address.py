###############################################################################
# $Id$
# Created 2005-??-??.
#
# Address classes.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Address classes."""
from bycycle.core.util import joinAttrs
from bycycle.core.model.point import Point
from bycycle.core.model.entities import StreetName, Place

__all__ = ['AddressError', 'Address', 'PostalAddress', 'EdgeAddress',
           'IntersectionAddress', 'PointAddress', 'NodeAddress']


class AddressError(Exception):
    pass


class Address(object):
    pass


class PostalAddress(Address):

    def __init__(self, number=None, street_name=None, place=None):
        try:
            number = int(number)
        except:
            pass
        self.number = number
        if street_name is None:
            street_name = StreetName()
        self.street_name = street_name
        if place is None:
            place = Place()
        self.place = place

    def _get_prefix(self):
        return self.street_name.prefix
    def _set_prefix(self, new_prefix):
        self.street_name.prefix = new_prefix
    prefix = property(_get_prefix, _set_prefix)

    def _get_name(self):
        return self.street_name.name
    def _set_name(self, new_name):
        self.street_name.name = new_name
    name = property(_get_name, _set_name)

    def _get_sttype(self):
        return self.street_name.sttype
    def _set_sttype(self, new_sttype):
        self.street_name.sttype = new_sttype
    sttype = property(_get_sttype, _set_sttype)

    def _get_suffix(self):
        return self.street_name.suffix
    def _set_suffix(self, new_suffix):
        self.street_name.suffix = new_suffix
    suffix = property(_get_suffix, _set_suffix)

    def _get_city(self):
        return self.place.city
    def _set_city(self, new_city):
        self.place.city = new_city
    city = property(_get_city, _set_city)

    def _get_city_id(self):
        return self.place.city_id
    def _set_city_id(self, id_):
        self.place.city_id = id_
    city_id = property(_get_city_id, _set_city_id)

    def _get_city_name(self):
        return self.place.city_name
    def _set_city_name(self, name):
        self.place.city_name = name
    city_name = property(_get_city_name, _set_city_name)

    def _get_state(self):
        return self.place.state
    def _set_state(self, new_state):
        self.place.state = new_state
    state = property(_get_state, _set_state)

    def _get_state_code(self):
        return self.place.state_code
    def _set_state_code(self, code):
        self.place.state_code = code
    state_code = property(_get_state_code, _set_state_code)

    def _get_state_name(self):
        return self.place.state_name
    def _set_state_name(self, name):
        self.place.state_name = name
    state_name = property(_get_state_name, _set_state_name)

    def _get_zip_code(self):
        return self.place.zip_code
    def _set_zip_code(self, new_zip_code):
        self.place.zip_code = new_zip_code
    zip_code = property(_get_zip_code, _set_zip_code)

    def __str__(self):
        result = joinAttrs([self.number, self.street_name])
        result = joinAttrs([result, self.place], '\n')
        return result

    def to_simple_object(self):
        return {
            'type': self.__class__.__name__,
            'number': self.number,
            'street_name': self.street_name,
            'place': self.place
        }

    def __repr__(self):
        return repr(self.to_simple_object())


class EdgeAddress(PostalAddress):

    def __init__(self, number=None, network_id=None, region_key=None):
        PostalAddress.__init__(self, number, place=Place())
        self.network_id = network_id
        self.region_key = region_key

    def __str__(self):
        s = PostalAddress.__str__(self)
        if s == str(PostalAddress()):
            s = str(
                '-'.join(
                    [str(a) for a in
                     (self.number, self.network_id, self.region_key)]
                )
            )
        return s


class IntersectionAddress(Address):

    def __init__(self,
                 street_name1=None, place1=None,
                 street_name2=None, place2=None):
        SN = StreetName
        self.street_name1 = street_name1 if street_name1 is not None else SN()
        self.street_name2 = street_name2 if street_name2 is not None else SN()
        place1 = place1 if place1 is not None else Place()
        place2 = place2 if place2 is not None else Place()
        if not place1:
            place1 = place2
        if not place2:
            place2 = place1
        self.place1, self.place2 = place1, place2

    def _get_prefix1(self):
        return self.street_name1.prefix
    def _set_prefix1(self, new_prefix1):
        self.street_name1.prefix = new_prefix1
    prefix1 = property(_get_prefix1, _set_prefix1)

    def _get_name1(self):
        return self.street_name1.name
    def _set_name1(self, new_name1):
        self.street_name1.name = new_name1
    name1 = property(_get_name1, _set_name1)

    def _get_sttype1(self):
        return self.street_name1.sttype
    def _set_sttype1(self, new_sttype1):
        self.street_name1.sttype = new_sttype1
    sttype1 = property(_get_sttype1, _set_sttype1)

    def _get_suffix1(self):
        return self.street_name1.suffix
    def _set_suffix1(self, new_suffix1):
        self.street_name1.suffix = new_suffix1
    suffix1 = property(_get_suffix1, _set_suffix1)

    def _get_city1(self):
        return self.place1.city
    def _set_city1(self, new_city1):
        self.place1.city = new_city1
    city1 = property(_get_city1, _set_city1)

    def _get_state1(self):
        return self.place1.state
    def _set_state1(self, new_state1):
        self.place1.state = new_state1
    state1 = property(_get_state1, _set_state1)

    def _get_zip_code1(self):
        return self.place1.zip_code
    def _set_zip_code1(self, new_zip_code1):
        self.place1.zip_code = new_zip_code1
    zip_code1 = property(_get_zip_code1, _set_zip_code1)

    def _get_prefix2(self):
        return self.street_name2.prefix
    def _set_prefix2(self, new_prefix2):
        self.street_name2.prefix = new_prefix2
    prefix2 = property(_get_prefix2, _set_prefix2)

    def _get_name2(self):
        return self.street_name2.name
    def _set_name2(self, new_name2):
        self.street_name2.name = new_name2
    name2 = property(_get_name2, _set_name2)

    def _get_sttype2(self):
        return self.street_name2.sttype
    def _set_sttype2(self, new_sttype2):
        self.street_name2.sttype = new_sttype2
    sttype2 = property(_get_sttype2, _set_sttype2)

    def _get_suffix2(self):
        return self.street_name2.suffix
    def _set_suffix2(self, new_suffix2):
        self.street_name2.suffix = new_suffix2
    suffix2 = property(_get_suffix2, _set_suffix2)

    def _get_city2(self):
        return self.place2.city
    def _set_city2(self, new_city2):
        self.place2.city = new_city2
    city2 = property(_get_city2, _set_city2)

    def _get_state2(self):
        return self.place2.state
    def _set_state2(self, new_state2):
        self.place2.state = new_state2
    state2 = property(_get_state2, _set_state2)

    def _get_zip_code2(self):
        return self.place2.zip_code
    def _set_zip_code2(self, new_zip_code2):
        self.place2.zip_code = new_zip_code2
    zip_code2 = property(_get_zip_code2, _set_zip_code2)

    def _get_street_name(self):
        return joinAttrs((self.street_name1, self.street_name2), ' & ')
    street_name = property(_get_street_name)

    def _get_place(self):
        if self.place2 is not None:
            return self.place2
        else:
            return self.place1
    place = property(_get_place)

    def __str__(self):
        return joinAttrs((self.street_name, self.place), '\n')

    def to_simple_object(self):
        return {
            'type': self.__class__.__name__,
            'street_name1': self.street_name1,
            'place1': self.place1,
            'street_name2': self.street_name2,
            'place2': self.place2
        }

    def __repr__(self):
        return repr(self.to_simple_object())


class PointAddress(IntersectionAddress):
    """Address constructed from a point object or a string repr of a point."""

    def __init__(self, point=None, x=None, y=None, z=None, region_key=None):
        IntersectionAddress.__init__(self)
        self.point = Point(point=point, x=x, y=y, z=z)
        self.region_key = region_key

    def _get_x(self):
        return self.point.x
    x = property(_get_x)

    def _get_y(self):
        return self.point.y
    y = property(_get_y)

    def _get_z(self):
        return self.point.z
    z = property(_get_z)

    def __str__(self):
        s = IntersectionAddress.__str__(self)
        if s == str(IntersectionAddress()):
            s = str(self.point)
        return s


class NodeAddress(IntersectionAddress):

    def __init__(self, network_id=None, region_key=None):
        IntersectionAddress.__init__(self)
        self.network_id = network_id
        self.region_key = region_key

    def __str__(self):
        s = IntersectionAddress.__str__(self)
        if s == str(IntersectionAddress()):
            s = str(
                '-'.join([str(a) for a in (self.network_id, self.region_key)])
            )
        return s
