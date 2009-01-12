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
        assert isinstance(route, Route)
        d = route.directions
        # KLUDGE: First turn should be EAST
        expected_turns = ['east', 'left', 'left', 'right']
        d_turns = [d[i]['turn'] for i in range(len(d))]
        print expected_turns
        print d_turns
        assert d_turns == expected_turns

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
        assert isinstance(routes, list)
        assert len(routes) == 2


if __name__ == '__main__':
    unittest.main()


"""
        Qs = {'milwaukeewi':
              (('Puetz Rd & 51st St', '841 N Broadway St'),
               ('27th and lisbon', '35th and w north'),
               ('S 84th Street & Greenfield Ave',
                'S 84th street & Lincoln Ave'),
               ('3150 lisbon', 'walnut & n 16th '),
               ('124th and county line, franklin', '3150 lisbon'),
               ('124th and county line, franklin',
                'x=-87.940407, y=43.05321'),
               ('x=-87.973645, y=43.039615',
                'x=-87.978623, y=43.036086'),
               ),
              'portlandor':
               (('x=-122.668104, y=45.523127', '4807 se kelly'),
                ('x=-122.67334,y=45.621662', '8220 N Denver Ave'),
                ('633 n alberta', '4807 se kelly'),
                ('sw hall & denney', '44th and se stark'),
                ('-122.645488, 45.509475', 'sw hall & denney'),
               ),
              }
"""
