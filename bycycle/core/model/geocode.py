###############################################################################
# $Id$
# Created 2005-??-??.
#
# Geocode classes.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Geocode classes."""
from urllib import quote_plus

__all__ = ['Geocode', 'PostalGeocode', 'IntersectionGeocode']


class Geocode(object):
    """Geocode base class.

    Attributes
    ----------

    ``address`` `Address` -- The associated address
    ``network_id`` `int` -- Either a node or edge ID
    ``xy`` `Point` -- Geographic location

    """

    def __init__(self, region, address, network_id, xy):
        """

        ``address`` -- `Address`
        ``network_id`` -- `Edge` or `Node` ID
        ``xy`` -- A point with x and y attributes

        """
        self.region = region
        self.address = address
        self.network_id = network_id
        self.xy = xy
        if xy is not None:
            xy_ll = region.proj(xy.x, xy.y, inverse=True)
        else:
            xy_ll = None
        self.xy_ll = xy_ll

    def __str__(self):
        return '\n'.join((str(self.address), str(self.xy)))

    def urlStr(self):
        # TODO: should do s_addr = self.address.urlStr()
        s_addr = str(self.address).replace('\n', ', ')
        # Build the "ID address" => num?, network ID, region key
        num = getattr(self.address, 'number', '')
        id_addr = ('%s-%s-%s' % (num, self.network_id, self.region.slug))
        id_addr = id_addr.lstrip('-')  # in case it's not postal
        s = ';'.join((s_addr, id_addr))
        return quote_plus(s)

    def to_simple_object(self):
        return {
            'type': self.__class__.__name__,
            'street_name': self.address.street_name.to_simple_object(),
            'place': self.address.place.to_simple_object(),
            'address': str(self.address),
            'point': self.xy,
            'network_id': self.network_id
        }

    def __repr__(self):
        return repr(self.to_simple_object())


class PostalGeocode(Geocode):
    """Represents a geocode that is associated with a postal address.

    ``address``
        `PostalAddress`
    ``edge``
        `Edge`
    ``xy`` `Point`
        Geographic location
    ``location``
        Location in [0, 1] of point in ``edge``

    """

    def __init__(self, region, address, edge):
        """

        ``address`` `PostalAddress`
        ``edge`` `Edge`

        """
        xy, location = edge.getPointAndLocationOfNumber(address.number)
        Geocode.__init__(self, region, address, edge.id, xy)
        self.location = location
        self.edge = edge

    def to_simple_object(self):
        return {
            'type': self.__class__.__name__,
            'number': self.address.number,
            'street_name': self.address.street_name.to_simple_object(),
            'place': self.address.place.to_simple_object(),
            'address': str(self.address),
            'point': {'x': self.xy.x, 'y': self.xy.y},
            'network_id': self.network_id
        }

    def __repr__(self):
        return repr(self.to_simple_object())

    def __eq__(self, other):
        """Compare two `PostalGeocode`s for equality """
        return (
            (self.network_id == other.network_id) and
            (self.address.number == other.address.number)
        )


class IntersectionGeocode(Geocode):
    """Represents a geocode that is associated with an intersection.

    Attributes
    ----------

    ``address`` `IntersectionAddress`
    ``node`` `Node`

    """

    def __init__(self, region, address, node):
        """

        ``address`` -- `IntersectionAddress`
        ``node`` -- `Node`

        """
        xy = node.geom
        Geocode.__init__(self, region, address, node.id, xy)
        self.node = node

    def to_simple_object(self):
        x = self.xy.x
        y = self.xy.y
        return {
            'type': self.__class__.__name__,
            'street_name1': self.address.street_name1.to_simple_object(),
            'street_name2': self.address.street_name2.to_simple_object(),
            'place1': self.address.place1.to_simple_object(),
            'place2': self.address.place2.to_simple_object(),
            'address': str(self.address),
            'point': {'x': x, 'y': y},
            'network_id': self.network_id
        }

    def __repr__(self):
        return repr(self.to_simple_object())

    def __eq__(self, other):
        """Compare two `IntersectionGeocode`s for equality """
        return (self.network_id == other.network_id)
