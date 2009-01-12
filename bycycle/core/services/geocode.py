###############################################################################
# $Id$
# Created ???.
#
# Geocode service.
#
# Copyright (C) 2006-2008 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Provides geocoding via the `query` method of the `Service` class.

Geocoding is the process of determining a location on earth associated with a
an address (or other feature). This service also determines which network
features input addresses are associated with and supplies this information
through the `Geocode` class as a node or edge ID, depending on the type of the
input address.

The service recognizes these types of addresses, which are first normalized by
the Address Normalization service (normaddr):

- Postal (e.g., 633 N Alberta, Portland, OR)
- Intersection (e.g., Alberta & Kerby)
- Point (e.g., x=-123, y=45)
- Node (i.e., node ID)
- Edge (i.e., number + edge ID).

"""
from sqlalchemy import orm
from sqlalchemy.sql import select, func, and_, or_
from sqlalchemy.orm.exc import NoResultFound

from bycycle.core.model import db
from bycycle.core.model import StreetName, City, State, Place
from bycycle.core.model.address import *
from bycycle.core.model.geocode import *

from bycycle.core import services
from bycycle.core.services import normaddr, identify
from bycycle.core.services.exceptions import *


class GeocodeError(ByCycleError):
    """Base Error class for Geocode service."""

    title = 'Geocode Service Error'
    description = ('An error was encountered in the geocoding service. '
                   'Further information is unavailable.')

    def __init__(self, description=None):
        ByCycleError.__init__(self, description)


class AddressNotFoundError(GeocodeError, NotFoundError):

    title = 'Address Not Found'
    description = 'Unable to find address.'
    explanation = """\
Reasons an address might not be found are...

* The spelling of the street name is incorrect.

* A numbered street was spelled out as a word. For example, instead of using "15th", you typed "fifteenth".

In general, street names must match exactly what you would see on a street sign.

A few other reasons are...

* The city, state, and zip code don't match or are incorrect. If in doubt, just leave the city, state, and zip code off entirely.

* The street direction (for example, "N" or "NE") is incorrect. If in doubt, leave off the direction.

* The street type, (for example, "Street" or "Road"), is incorrect. If in doubt, leave off the street type.

If you try all of these things and the address still isn't found, you can try the "find address at center" link at the top left of the map. Zoom in on the location you're interested in and center the red dot over it, then click the link. This will find the closest intersection, which is usually close enough.
"""

    def __init__(self, address, region=None):
        desc = ['Unable to find address "%s"' % address]
        if region is not None:
            desc.append('in %s' % region.title)
        desc = ' '.join(desc) + '.'
        GeocodeError.__init__(self, desc)


class MultipleAddressesNotFoundError(AddressNotFoundError):

    title = 'Addresses Not Found'

    def __init__(self, addresses, region=None):
        if len(addresses) == 1:
            raise AddressNotFoundError(addresses[0], region)
        desc = ('Unable to find addresses: "%s".' %
                '", "'.join([a for a in addresses]))
        GeocodeError.__init__(self, desc)


class MultipleMatchingAddressesError(GeocodeError):

    title = 'Multiple Matching Addresses Found'
    description = 'Multiple addresses were found that match the input address.'

    def __init__(self, geocodes=[]):
        self.geocodes = geocodes
        GeocodeError.__init__(self)


class Service(services.Service):
    """Geocoding Service."""

    name = 'geocode'

    def query(self, q, **kwargs):
        """Find and return `Geocodes` in ``region`` matching the address ``q``.

        Choose the appropriate geocoding method based on the type of the input
        address. Call the geocoding method and return a `Geocode`. If the
        input address can't be found or there is more than one match for it,
        an exception will be raised.

        ``q`` `string`
            An address to be normalized & geocoded in the given ``region``.

        return `Geocode`
            A `Geocode` object corresponding to the input address, ``q``.

        raise `ValueError`
            Type of input address can't be determined

        raise `InputError`, `ValueError`
            Some are raised in the normaddr query. Look there for details.

        raise `AddressNotFoundError`
            The address can't be geocoded

        raise `MultipleMatchingAddressesError`
            Multiple address found that match the input address, ``q``

        """
        self.query_kwargs = kwargs

        # First, normalize the address, getting back an `Address` object.
        # The NA service may find a region, iff `region` isn't already set. If
        # so, we want to use that region as the region for this query.
        na_service = normaddr.Service(region=self.region)
        oAddr = na_service.query(q, **self.query_kwargs)
        self.region = na_service.region

        module = self.region.module
        g = globals()
        entities = 'Edge', 'Node'
        for name in entities:
            g[name] = getattr(module, name)

        if isinstance(oAddr, (NodeAddress, PointAddress)):
            geocodes = self.getPointGeocodes(oAddr)
        elif isinstance(oAddr, (EdgeAddress, PostalAddress)):
            geocodes = self.getPostalGeocodes(oAddr)
        elif isinstance(oAddr, IntersectionAddress):
            try:
                geocodes = self.getIntersectionGeocodes(oAddr)
            except AddressNotFoundError, _not_found_exc:
                # Couldn't find something like "48th & Main" or "Main & 48th"
                # Try "4800 Main" instead
                try:
                    num = int(oAddr.street_name1.name[:-2])
                except (TypeError, ValueError):
                    try:
                        num = int(oAddr.street_name2.name[:-2])
                    except (TypeError, ValueError):
                        pass
                    else:
                        street_name = oAddr.street_name1
                else:
                    street_name = oAddr.street_name2

                try:
                    postal_addr = PostalAddress(number=num*100,
                                                street_name=street_name,
                                                place=oAddr.place)
                    geocodes = self.getPostalGeocodes(postal_addr)
                except (NameError, UnboundLocalError, AddressNotFoundError), e:
                    # Neither of the cross streets had a number street name OR
                    # the faked postal address couldn't be found.
                    raise _not_found_exc
        else:
            raise ValueError('Could not determine address type for address '
                             '"%s" in region "%s"' %
                             (q, region or '[No region specified]'))

        if len(geocodes) > 1:
            raise MultipleMatchingAddressesError(geocodes=geocodes)

        return geocodes[0]

    ### Each get*Geocode function returns a list of possible geocodes for the
    ### input address or raises an error when no matches are found.

    def getPostalGeocodes(self, oAddr):
        """Geocode postal address represented by ``oAddr``.

        ``oAddr``
            A `PostalAddress` (e.g., 123 Main St, Portland) OR an
            `EdgeAddress`. An edge "address" contains just street number and
            ID of some edge.

        return `list`
            A list of `PostalGeocode`s.

        raise ``AddressNotFoundError``
            Address doesn't match any edge in the database.

        """
        geocodes = []
        num = oAddr.number
        q = db.Session.query(Edge)

        clause = [or_(
            and_(num >= func.least(Edge.addr_f_l, Edge.addr_f_r),
                 num <= func.greatest(Edge.addr_t_l, Edge.addr_t_r)),
            and_(num >= func.least(Edge.addr_t_l, Edge.addr_t_r),
                 num <= func.greatest(Edge.addr_f_l, Edge.addr_f_r))
        )]

        try:
            # Try to look up edge by network ID first
            network_id = oAddr.network_id
        except AttributeError:
            # No network ID, so look up address by street name and place
            self.append_street_name_where_clause(clause, oAddr.street_name)
            self.append_place_where_clause(clause, oAddr.place)
            edges = q.filter(and_(*clause)).all()
        else:
            clause.append(Edge.id == network_id)
            edges = q.filter(and_(*clause)).all()

        if not edges:
            raise AddressNotFoundError(address=oAddr, region=self.region)

        # Make list of geocodes for edges matching oAddr
        for e in edges:
            place = e.getPlaceOnSideNumberIsOn(num)
            e_addr = PostalAddress(num, e.street_name, place)
            geocodes.append(PostalGeocode(self.region, e_addr, e))
        return geocodes

    def getIntersectionGeocodes(self, oAddr):
        """Geocode the intersection address represented by ``oAddr``.

        ``oAddr`` -- An `IntersectionAddress` (e.g., 1st & Main, Portland)

        return `list` -- A list of `IntersectionGeocode`s.

        raise `AddressNotFoundError` -- Address doesn't match any edges in the
        database.

        """
        def get_node_ids(street_name, place):
            """Get `set` of node IDs for ``street_name`` and ``place``."""
            ids = set()
            select_ = select([Edge.node_f_id, Edge.node_t_id], bind=db.engine)
            self.append_street_name_where_clause(select_, street_name)
            self.append_place_where_clause(select_, place)
            result = select_.execute()
            map(ids.update, ((r.node_f_id, r.node_t_id) for r in result))
            return ids

        node_ids = get_node_ids(oAddr.street_name1, oAddr.place1)
        if node_ids:
            other_ids = get_node_ids(oAddr.street_name2, oAddr.place2)
            node_ids = node_ids & other_ids

        if not node_ids:
            raise AddressNotFoundError(address=oAddr, region=self.region)

        # Get node rows matching common node IDs and map to `Node` objects
        nodes = Node.get(node_ids)

        if not nodes:
            raise AddressNotFoundError(address=oAddr, region=self.region)

        # Create and return `IntersectionGeocode`s
        geocodes = []
        for node in nodes:
            edges = node.edges

            # Score the node's edges, finding the ones that best match the
            # cross streets of the input address
            best_score1, edge1 = 0, None
            best_score2, edge2 = 0, None
            for e in edges:
                street_name = e.street_name
                place_l, place_r = e.place_l, e.place_r
                score_1, score_2 = 0, 0
                for attr in ('prefix', 'name', 'sttype', 'suffix'):
                    e_val = getattr(street_name, attr, None)
                    if e_val == getattr(oAddr.street_name1, attr):
                        score_1 += 1
                    if e_val == getattr(oAddr.street_name2, attr):
                        score_2 += 1
                for attr in ('city', 'state', 'zip_code'):
                    e_l_val = getattr(place_l, attr, None)
                    e_r_val = getattr(place_r, attr, None)
                    if getattr(oAddr.place1, attr) in (e_l_val, e_r_val):
                        score_1 += 1
                    if getattr(oAddr.place2, attr) in (e_l_val, e_r_val):
                        score_2 += 1
                # Are the scores for this edge better than the previous best
                # scores for the previous best-matching edges?
                if score_1 > best_score1:
                    best_score1, edge1 = score_1, e
                if score_2 > best_score2:
                    best_score2, edge2 = score_2, e

            addr = IntersectionAddress(
                street_name1=edge1.street_name, place1=edge1.place_l,
                street_name2=edge2.street_name, place2=edge2.place_l
            )
            g = IntersectionGeocode(self.region, addr, node)
            geocodes.append(g)
        return geocodes

    def getPointGeocodes(self, oAddr):
        """Geocode point or node address represented by ``oAddr``.

        ``oAddr``
            A `PointAddress` (e.g., POINT(x y)) OR a `NodeAddress`. A node
            "address" contains just the ID of some node.

        return `list`
            A list containing one `IntersectionGeocode` or one
            `PostalGeocode`, depending on whether the point is at an
            intersection with cross streets or a dead end.

        raise `AddressNotFoundError`
            Point doesn't match any nodes in the database.

        """
        try:
            # Special case of `Node` ID supplied directly
            node_id = oAddr.network_id
        except AttributeError:
            # No network ID, so look up `Node` by distance
            id_service = identify.Service(region=self.region)
            try:
                node = id_service.query(
                    oAddr.point, layer='Node', **self.query_kwargs)
            except IdentifyError:
                node = None
        else:
            node = Node.get(node_id)

        # TODO: Check the `Edge`'s street names and places for [No Name]s and
        # choose the `Edge`(s) that have the least of them. Also, we should
        # pick streets that have different names from each other when creating
        # `IntersectionAddresses`s
        if node is not None:
            edges = node.edges
        else:
            raise AddressNotFoundError(region=self.region, address=oAddr)
        if len(edges) > 1:
            # `node` has multiple outgoing edges
            edge1, edge2 = edges[0], edges[1]
            addr = IntersectionAddress(
                street_name1=edge1.street_name, place1=edge1.place_l,
                street_name2=edge2.street_name, place2=edge2.place_l
            )
            g = IntersectionGeocode(self.region, addr, node)
        else:
            # `node` is at a dead end
            edge = edges[0]
            # Set address number to number at `node` end of edge
            if node.id == edge.node_f_id:
                num = edge.addr_f_l or edge.addr_f_r
            else:
                num = edge.addr_t_l or edge.addr_t_r
            addr = PostalAddress(num, edge.street_name, edge.place_l)
            g = PostalGeocode(self.region, addr, edge)
            g.node = node
        return [g]

    ### Utilities

    def get_street_name_ids(self, street_name):
        """Get a WHERE clause for ``street_name``."""
        clause = []
        for name in ('prefix', 'name', 'sttype', 'suffix'):
            val = getattr(street_name, name)
            if val:
                clause.append(getattr(StreetName, name) == val)
        if clause:
            result = select(
                [StreetName.id], and_(*clause), bind=db.engine).execute()
            return [r.id for r in result]
        return []

    def append_street_name_where_clause(self, append_to, street_name):
        if street_name:
            st_name_ids = self.get_street_name_ids(street_name)
            clause = Edge.street_name_id.in_(st_name_ids)
            if isinstance(append_to, (list, tuple)):
                append_to.append(clause)
            else:
                append_to.append_whereclause(clause)

    def get_place_ids(self, place):
        """Get ``Place`` ``place``."""
        clause = []
        if place.city_name:
            r = select(
                [City.id], (City.city == place.city_name),
                bind=db.engine).execute()
            city_id = r.fetchone().id if r.rowcount else None
            clause.append(Place.city_id == city_id)
        if place.state_code:
            r = select(
                [State.id], (State.code == place.state_code),
                bind=db.engine).execute()
            state_id = r.fetchone().id if r.rowcount else None
            clause.append(Place.state_id == state_id)
        if place.zip_code:
            clause.append(Place.zip_code == place.zip_code)
        if clause:
            result = select([Place.id], and_(*clause), bind=db.engine).execute()
            return [r.id for r in result]
        return []

    def append_place_where_clause(self, append_to, place):
        if place:
            place_ids = self.get_place_ids(place)
            clause = or_(
                Edge.place_l_id.in_(place_ids),
                Edge.place_r_id.in_(place_ids)
            )
            if isinstance(append_to, (list, tuple)):
                append_to.append(clause)
            else:
                append_to.append_whereclause(clause)
