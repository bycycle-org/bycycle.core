###############################################################################
# $Id$
# Created 2006-??-??.
#
# Unit tests for ``Address`` classes.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Unit tests for `Address` classes.

"""
import unittest
from byCycle.model.address import *
from byCycle.model.entities import *


class TestPostalAddress(unittest.TestCase):
    """Test creation of `PostalAddress`es."""

    def test_PostalAddress(self):
        oAddr = PostalAddress(
            number='4807',
            street_name=StreetName(
                prefix='SE',
                name='Kelly',
                sttype='St'
            ),
            place=Place(
                city=City(city='Portland'),
                state=State(code='OR'),
                zip_code=97206
            )
        )
        self.assertEqual(str(oAddr), '4807 SE Kelly St\nPortland, OR 97206')
        oAddr.prefix = 'N';
        self.assertEqual(oAddr.prefix, 'N')
        self.assertEqual(oAddr.street_name.prefix, 'N')
        oAddr.name = 'Alberta'
        self.assertEqual(oAddr.name, 'Alberta')
        self.assertEqual(oAddr.street_name.name, 'Alberta')
        oAddr.sttype = 'Rd'
        self.assertEqual(oAddr.sttype, 'Rd')
        self.assertEqual(oAddr.street_name.sttype, 'Rd')
        oAddr.suffix = 'SB'
        self.assertEqual(oAddr.suffix, 'SB')
        self.assertEqual(oAddr.street_name.suffix, 'SB')


class TestIntersectionAddress(unittest.TestCase):
    """Test creation of `IntersectionAddress`es."""

    def test_IntersectionAddress(self):
        oAddr = IntersectionAddress(
            street_name1=StreetName(
                prefix='SE',
                name='Kelly',
                sttype='St'
            ),
            place1=Place(
                city=City(city='Portland'),
                state=State(code='OR'),
                zip_code=97206
            ),
            street_name2=StreetName(
                prefix='SE',
                name='49th',
                sttype='Ave'
            ),
            place2=Place(
                city=City(city='Portland'),
                state=State(code='OR'),
                zip_code=97206
            )
        )
        sAddr = 'SE Kelly St & SE 49th Ave\nPortland, OR 97206'
        assert(str(oAddr) == sAddr)
        

class TestPointAddress(unittest.TestCase):
    """Test creation of `PointAddress`es."""
    
    def test_WKT(self):
        oAddr = PointAddress(x=-123.12, y=45)
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')
        
    def test_Eval(self):
        oAddr = PointAddress(point='(-123.12, 45)')
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')
        oAddr = PointAddress(point='{"x": -123.12, "y": 45}')
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')
        
    def test_Kwargs(self):
        oAddr = PointAddress(point='x=-123.12, y=45')
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')

    def test_Dict(self):
        oAddr = PointAddress(point={'x': -123.12, 'y': 45})
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')

    def test_Object(self):
        class P:
            x = -123.12
            y = 45
        oAddr = PointAddress(point=P())
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')

    def test_Sequence(self):
        oAddr = PointAddress(point=(-123.12, 45))
        self.assertEqual(str(oAddr), 'POINT (-123.120000 45.000000)')        
        
        
if __name__ == "__main__":
    unittest.main()
