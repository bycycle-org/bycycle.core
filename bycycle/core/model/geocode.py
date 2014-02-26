"""Geocode classes."""
from urllib.parse import quote_plus

from shapely.geometry import Point, mapping

from bycycle.core.model.entities.base import Entity


__all__ = ['Geocode', 'PostalGeocode', 'IntersectionGeocode']


class Geocode(Entity):
    """Geocode base class.

    Attributes
    ----------

    ``address`` `Address` -- The associated address
    ``network_id`` `int` -- Either a node or edge ID
    ``xy`` `Point` -- Geographic location

    """

    member_name = 'geocode'
    collection_name = 'geocodes'
    member_title = 'Geocode'
    collection_title = 'Geocodes'

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
            lon, lat = region.proj(xy.x, xy.y, inverse=True)
            self.lat_long = Point(lon, lat)
        else:
            self.lat_long = None

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

    def to_simple_object(self, fields=None):
        xy = self.xy
        lat_long = self.lat_long
        if xy is not None:
            xy = mapping(xy)
        if lat_long is not None:
            lat_long = mapping(lat_long)
        return {
            'type': self.__class__.__name__,
            'address': str(self.address),
            'point': xy,
            'lat_long': lat_long,
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

    def to_simple_object(self, fields=None):
        obj = super(PostalGeocode, self).to_simple_object(fields)
        obj.update({
            'number': self.address.number,
            'street_name': self.address.street_name.to_simple_object(),
        })
        return obj

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

    def to_simple_object(self, fields=None):
        obj = super(IntersectionGeocode, self).to_simple_object(fields)
        obj.update({
            'street_name': self.address.street_name,
            'street_name1': self.address.street_name1.to_simple_object(),
            'street_name2': self.address.street_name2.to_simple_object(),
            'place1': self.address.place1.to_simple_object(),
            'place2': self.address.place2.to_simple_object(),
        })
        return obj

    def __eq__(self, other):
        """Compare two `IntersectionGeocode`s for equality """
        return (self.network_id == other.network_id)
