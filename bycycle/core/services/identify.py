###############################################################################
# $Id: identify.py 335 2006-11-16 01:39:00Z bycycle $
# Created 2006-11-16.
#
# Identify service.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
"""In a region and layer within that region, find feature nearest point.

Given a region (i.e., data source), a layer within that region, and a point, find the feature nearest the point and return an object representing that feature.

"""
from sqlalchemy.sql import select, func
from sqlalchemy.orm.exc import NoResultFound

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
        earth_circumference = region.earth_circumference
        Entity = getattr(region.module, layer)
        c = Entity.__table__.c
        # Get "well known text" version of input ``point``
        wkt = str(point)
        # Transform WKT point to DB geometry object
        transform = func.GeomFromText(wkt, input_srid)
        # Function to convert input ``point`` to native geometry
        if input_srid != region.srid:
            transform = func.transform(transform, region.srid)
        # Function to get the distance between input point and table points
        distance = func.distance(transform, c.geom)
        # This is what we're SELECTing--all columns in the layer plus the
        # distance from the input point to points in the nodes table (along
        # with the node ID and geom).
        cols = c + [distance.label('distance')]
        # Limit the search to within `expand_dist` feet of the input point.
        # Keep trying until we find a match or until `expand_dist` is
        # larger than half the circumference of the earth.
        expand_dist = region.block_length
        overlaps = c.geom.op('&&')  # geometry A overlaps geom B operator
        expand = func.expand  # geometry bounds expanding function
        db_q = db.Session.query(*cols)
        while expand_dist < earth_circumference:
            where = overlaps(expand(transform, expand_dist))
            row = db_q.filter(where).order_by('distance').first()
            if row is None:
                expand_dist *= 2
            else:
                return Entity.get(row.id)
        raise IdentifyError(
            'Could not identify feature nearest to "%s" in region "%s", layer '
            '"%s"' % (q, region, layer))
