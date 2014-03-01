"""Geocode classes."""
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

    def __json_data__(self):
        xy = self.xy
        lat_long = self.lat_long
        if xy is not None:
            xy = mapping(xy)
        if lat_long is not None:
            lat_long = mapping(lat_long)
        return {
            'type': self.__class__.__name__,
            'id': self.id,
            'address': str(self.address),
            'point': xy,
            'lat_long': lat_long,
            'network_id': self.network_id
        }

    def __repr__(self):
        return repr(self.__json_data__())


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
        self.id = '{}-{}-{}'.format(
            address.number, self.network_id, self.region.slug)
        self.location = location
        self.edge = edge

    def __json_data__(self):
        obj = super(PostalGeocode, self).__json_data__()
        obj.update({
            'number': self.address.number,
            'street_name': self.address.street_name.__json_data__(),
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
        self.id = '{}-{}'.format(self.network_id, self.region.slug)
        self.node = node

    def __json_data__(self):
        obj = super(IntersectionGeocode, self).__json_data__()
        obj.update({
            'street_name': self.address.street_name,
            'street_name1': self.address.street_name1.__json_data__(),
            'street_name2': self.address.street_name2.__json_data__(),
            'place1': self.address.place1.__json_data__(),
            'place2': self.address.place2.__json_data__(),
        })
        return obj

    def __eq__(self, other):
        """Compare two `IntersectionGeocode`s for equality """
        return (self.network_id == other.network_id)
