import unittest

from bycycle.core.util import django_setup

try:
    django_setup()
except RuntimeError:
    pass

from bycycle.core.models import LookupResult
from bycycle.core.services import LookupService
from bycycle.core.services.lookup import MultipleLookupResultsError


class TestLookupService(unittest.TestCase):
    def _query(self, query, point_hint=None) -> LookupResult | None:
        service = LookupService()
        return service.query(query, point_hint)

    def test_query_point_string(self):
        result = self._query("45.548242, -122.672655")
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, "N Fremont St")

    def test_query_point_wkt(self):
        result = self._query("POINT(-122.672655 45.548242)")
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, "N Fremont St")

    def test_query_cross_streets(self):
        try:
            result = self._query("NE 9th and Holladay")
        except MultipleLookupResultsError as exc:
            results = exc.choices
        else:
            results = [result]
        for result in results:
            self.assertIsInstance(result, LookupResult)
            self.assertEqual(result.name, "NE 9th Ave & NE Holladay St")
