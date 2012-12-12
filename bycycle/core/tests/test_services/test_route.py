################################################################################
# $Id: testgeocode.py 208 2006-09-11 03:41:35Z bycycle $
# Created 2006-09-25.
#
# Unit tests for route service.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
import unittest

from bycycle.core.services.route import *
from bycycle.core.model.route import Route


class Test_A_Route(unittest.TestCase):

    def _query(self, q, region=None, **kwargs):
        service = Service(region=region)
        route_or_routes = service.query(q, **kwargs)
        return route_or_routes

    def _queryRaises(self, q, exc):
        self.assertRaises(exc, self._query, q)

    def test_should_have_specific_turns(self):
        q = ('4807 se kelly, portland, or', '45th and division, portland, or')
        route = self._query(q)
        self.assertIsInstance(route, Route)
        d = route.directions
        # KLUDGE: First turn should be EAST
        expected_turns = ['east', 'left', 'left', 'right']
        d_turns = [d[i]['turn'] for i in range(len(d))]
        self.assertEqual(d_turns, expected_turns)

    def test_with_coordinate_addresses_should_pass(self):
        q = ('x=-122.668104, y=45.523127', '4807 se kelly')
        route = self._query(q, region='portlandor', input_srid=4326)
        q = ('4807 se kelly', 'longitude=-122.668104, latitude=45.523127')
        route = self._query(q, region='portlandor', input_srid=4326)
        q = ('x=-122.668104, lat=45.523127',
             'longitude=-122.615426, latitude=45.502625')
        route = self._query(q, region='portlandor', input_srid=4326)

    def test_with_no_place_on_first_address_should_pass_but_does_not(self):
        # FIXME: Make this NOT pass (then change the name of the test)
        q = ('4807 se kelly', '633 n alberta, portland, or')
        routes = self._queryRaises(q, InputError)

    def test_with_no_place_on_second_address_should_be_ok(self):
        q = ('4807 se kelly, portland, or', '633 n alberta')
        routes = self._query(q)

    def test_with_three_addresses_should_return_a_list_with_2_routes(self):
        q = ('4807 se kelly, portland, or', '633 n alberta', '1500 ne alberta')
        routes = self._query(q)
        self.assertIsInstance(routes, list)
        self.assertEqual(len(routes), 2)

    def test_intersection_addresses(self):
        q = ('NW 17th and Couch', 'SE 21st and Clinton')
        route = self._query(q, region='portlandor')
        self.assertIsInstance(route, Route)

    def test_synthetic_destination_node_directly_after_last_turn(self):
        """
        Test the special case where there are no intersections between
        the last turn in a route and a synthetic destination node. This
        situation is depicted below where "O" is the start location, "X"
        is the end, and "*"s are intersections.

                                *---X---*
                                |
                                |
                                |
                                *
                                |
                                |
                                |
                *-------*-------*
                |
                |
                |
        *--O----*

        """
        q = ('1815 nw couch', '633 n alberta')
        route = self._query(q, region='portlandor')
        self.assertIsInstance(route, Route)
        d = route.directions
        self.assertIs(d[-1]['toward'], None)


if __name__ == '__main__':
    unittest.main()
