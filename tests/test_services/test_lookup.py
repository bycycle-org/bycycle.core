import unittest

from bycycle.core.util import django_setup

django_setup()

from bycycle.core.models import LookupResult
from bycycle.core.services import LookupService


class TestLookupService(unittest.TestCase):
    def _query(self, q, **kwargs):
        service = LookupService()
        return service.query(q, **kwargs)

    def test_lookup_point(self):
        result = self._query("45.548242, -122.672655")
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, "N Fremont St")

    def test_lookup_cross_streets(self):
        result = self._query("NE 9th and Holladay")
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.name, "NE 9th Ave & NE Holladay St")
