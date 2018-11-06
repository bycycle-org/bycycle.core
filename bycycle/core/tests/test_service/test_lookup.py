import unittest

from bycycle.core.model import get_engine, get_session_factory, LookupResult
from bycycle.core.service import LookupService


class TestLookupService(unittest.TestCase):

    def setUp(self):
        self.engine = get_engine()
        self.session_factory = get_session_factory(self.engine)
        self.session = self.session_factory()

    def tearDown(self):
        self.engine.dispose()
        self.session.close()

    def _query(self, q, **kwargs):
        service = LookupService(self.session)
        return service.query(q, **kwargs)

    def test_lookup_point(self):
        result = self._query('-122.672655, 45.548242')
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, 'N Fremont St')

    def test_lookup_cross_streets(self):
        result = self._query('NE 9th and Holladay')
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, 'NE 9th Ave & NE Holladay St')
