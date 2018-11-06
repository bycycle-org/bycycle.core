import unittest

from bycycle.core.model import get_engine, get_session_factory, Route
from bycycle.core.service.route import RouteService


class Test_A_Route(unittest.TestCase):

    def setUp(self):
        self.engine = get_engine()
        self.session_factory = get_session_factory(self.engine)
        self.session = self.session_factory()

    def tearDown(self):
        self.engine.dispose()
        self.session.close()

    def _query(self, q, **kwargs):
        service = RouteService(self.session)
        return service.query(q, **kwargs)

    def test_should_have_specific_turns(self):
        q = 'NE 9th and Holladay', 'NE 15th and Broadway'
        route = self._query(q)
        self.assertIsInstance(route, Route)
        d = route.directions
        expected_turns = ['east', 'left', 'right', 'left', 'left', 'right', 'left']
        d_turns = [d[i]['turn'] for i in range(len(d))]
        self.assertEqual(d_turns, expected_turns)

    def test_with_three_addresses_should_return_a_list_with_2_routes(self):
        q = 'NE 9th and Holladay', 'NE 15th and Broadway', 'NE 21st and Weidler'
        routes = self._query(q)
        self.assertIsInstance(routes, list)
        self.assertEqual(len(routes), 2)

    def test_intersection_addresses(self):
        q = 'NW 17th and Couch', 'SE 21st and Clinton'
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
        q = 'NW 18th and Couch', '-122.672655, 45.548242'
        route = self._query(q)
        self.assertIsInstance(route, Route)
        d = route.directions
        self.assertIs(d[-1]['toward'], None)

    def test_same_start_and_end(self):
        q = '3rd and Burnside', '3rd and Burnside'
        route = self._query(q)
        self.assertEqual(route.start.id, route.end.id)

    def test_same_start_and_end_point(self):
        q = '-122.69891, 45.53763', '-122.69891, 45.53763'
        route = self._query(q)
        self.assertEqual(route.start.id, route.end.id)


if __name__ == '__main__':
    unittest.main()
