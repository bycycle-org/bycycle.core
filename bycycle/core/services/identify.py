"""In a region and layer within that region, find feature nearest point.

Given a region (i.e., data source), a layer within that region, and a point, find the feature nearest the point and return an object representing that feature.

"""
from sqlalchemy.sql import func

from bycycle.core.model import db
from bycycle.core.model.point import Point
from bycycle.core import services
from bycycle.core.services.exceptions import IdentifyError


class Service(services.Service):
    """Identify Service."""

    name = 'identify'

    def query(self, q, layer=None, input_srid=None, **kwargs):
        """Find feature in layer closest to point represented by ``q``.

        ``q``
            A Point object or a string representing a point.

        ``layer``
            The layer to search

        ``input_srid``
            The SRID of the input point represented by ``q``

        return
            A domain object representing the feature nearest to ``q``.

        raise ValueError
            ``q`` can't be parsed as valid point.

        """
        region = self.region
        try:
            point = Point(q)
        except ValueError:
            raise IdentifyError(
                'Cannot identify because POINT is not valid: %s.' % q)
        input_srid = input_srid or region.srid
        Entity = getattr(region.module, layer)
        # Get "well known text" version of input ``point``
        wkt = str(point)
        # Transform WKT point to DB geometry object
        geom = func.ST_GeomFromText(wkt, input_srid)
        # Function to convert input ``point`` to native geometry
        if input_srid != region.srid:
            geom = func.st_transform(geom, region.srid)
        # Function to get the distance between input point and table points
        distance = func.st_distance(geom, Entity.geom)
        q = db.Session.query(Entity, distance.label('distance'))
        q = q.order_by(distance)
        record = q.first()
        if record is None:
            raise IdentifyError(
                'Could not identify feature nearest to "%s" in region "%s", '
                'layer "%s"' % (q, region, layer))
        return record[0]
