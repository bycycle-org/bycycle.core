from django.test import TestCase

from bycycle.core.models import Street
from bycycle.core.models import util


class TestUtil(TestCase):

    def test_get_extent(self):
        util.get_extent(Street)
