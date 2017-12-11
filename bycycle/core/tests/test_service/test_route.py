import unittest

from bycycle.core import db
from bycycle.core.exc import InputError
from bycycle.core.model import Route
from bycycle.core.service.route import RouteService


class Test_A_Route(unittest.TestCase):

    def setUp(self):
        self.engine, self.session_factory = db.init()
        self.session = self.session_factory()

    def tearDown(self):
        self.session.close()

    def _query(self, q, **kwargs):
        service = RouteService(self.session)
        route_or_routes = service.query(q, **kwargs)
        return route_or_routes

    def test_should_have_specific_turns(self):
        q = ('4807 se kelly, portland, or', '45th and division, portland, or')
        route = self._query(q)
        self.assertIsInstance(route, Route)
        d = route.directions
        # KLUDGE: First turn should be EAST
        expected_turns = ['west', 'right']
        d_turns = [d[i]['turn'] for i in range(len(d))]
        self.assertEqual(d_turns, expected_turns)

    def test_with_coordinate_addresses_should_pass(self):
        self._query(['-122.668104,45.523127', '-122.615426,45.502625'])
        # q = ('-122.668104,45.523127', '4807 se kelly')
        # self._query(q)
        # q = ('4807 se kelly', '-122.668104,45.523127')
        # self._query(q)

    def test_with_no_place_on_first_address_should_pass_but_does_not(self):
        # FIXME: Make this NOT pass (then change the name of the test)
        q = ('4807 se kelly', '633 n alberta, portland, or')
        self.assertRaises(InputError, self._query, q)

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
        route = self._query(q)
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
        route = self._query(q)
        self.assertIsInstance(route, Route)
        d = route.directions
        self.assertIs(d[-1]['toward'], None)


if __name__ == '__main__':
    unittest.main()
