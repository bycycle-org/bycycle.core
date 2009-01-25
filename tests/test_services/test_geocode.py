################################################################################
# $Id$
# Created 2006-??-??.
#
# Unit tests for geocode service.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
import unittest
from byCycle.util import meter
from byCycle.model.geocode import *
from byCycle.services.geocode import *


quiet = 1
if not quiet:
    timer = meter.Timer()


class TestPortlandOR(unittest.TestCase):

    service = Service(region='portlandor')

    def _query(self, q):
        if not quiet:
            print '\n*****', q
            timer.start()
        _geocode = self.service.query(q)
        self.assert_(isinstance(_geocode, Geocode))
        if not quiet:
            print timer.stop(), 'seconds\n'
        return _geocode

    def _queryRaises(self, q, exc):
        self.assertRaises(exc, self._query, q)

    ### Edge

    def test_EdgeAddress(self):
        # Get street name ID for n alberta st
        StreetName = self.service.region.module.StreetName
        Edge = self.service.region.module.Edge
        c = StreetName.c
        street_name = StreetName.selectfirst((c.prefix == 'n') &
                                             (c.name == 'alberta') & 
                                             (c.sttype == 'st'))
        street_name_id = street_name.id

        # Get edge matching 633 n alberta st        
        c = Edge.c
        edge = Edge.selectfirst((c.addr_f_l <= 633) & (c.addr_t_l >= 633) &
                                (c.street_name_id == street_name_id))
        network_id = edge.id
        
        q = '633-%s' % network_id
        geocode = self._query(q)

    def test_EdgeAddress_BadID(self):
        q = '633-1651035434'
        self.assertRaises(AddressNotFoundError, self._query, q)

    ### Intersection

    def test_IntersectionAddress_BothPlaces(self):
        q = ('W Burnside St, Portland, OR 97204 AND '
             'NW 3rd Ave, Portland, OR 97209')
        geocode = self._query(q)

    def test_IntersectionAddress_DisambiguatedMultipleMatch(self):
        q = '3rd / main 97024'
        geocode = self._query(q)

    def test_IntersectionAddress_Midblock(self):
        q = '48th & kelly'
        geocode = self._query(q)

    def test_IntersectionAddress_MultipleMatches(self):
        q = '3rd @ main'
        self._queryRaises(q, MultipleMatchingAddressesError)
        try:
            self._query(q)
        except MultipleMatchingAddressesError, e:
            self.assert_(len(e.geocodes) == 10)

    def test_IntersectionAddress_NoPlace(self):
        q = '44th and stark'
        geocode = self._query(q)

    def test_IntersectionAddress_OnlyPlace1(self):
        q = 'Burnside St, Portland, OR 97209 AT 3rd Ave'
        geocode = self._query(q)

    def test_IntersectionAddress_OnlyPlace2(self):
        q = 'Burnside St & 3rd Ave, Portland, OR 97209'
        geocode = self._query(q)

    ### Node

    def test_NodeAddress(self):
        n = self.service.region.module.Node.selectfirst()
        q = str(n.id)
        geocode = self._query(q)

    def test_NodeAddress_BadID(self):
        q = '8474400'
        self._queryRaises(q, AddressNotFoundError)

    ### Point

    def test_PointAddress_KwargsString(self):
        q = 'x=-120.432129, y=46.137977'
        geocode = self._query(q)
        q = 'lon=-122.609138, lat=45.497383'
        geocode = self._query(q)

    def test_PointAddress_PositionalKwargsString(self):
        q = 'asldfj=-123.432129, aass=46.137977'
        geocode = self._query(q)

    def test_PointAddress_StringTuple_Parens(self):
        q = '(-122.67334, 45.523307)'
        geocode = self._query(q)

    def test_PointAddress_StringTuple_NoParens(self):
        q = '-122.67334, 45.523307'
        geocode = self._query(q)

    def test_PointAddress_WKT_1(self):
        q = 'POINT(-120.432129 46.137977)'
        geocode = self._query(q)

    def test_PointAddress_WKT_2(self):
        q = 'POINT(-120.025635 45.379161)'
        geocode = self._query(q)

    ### Postal

    def test_PostalAddress_AllPartsNoCommas(self):
        q = '4408 se stark st oregon 97215'
        geocode = self._query(q)

    def test_PostalAddress_BadState(self):
        q = '4408 se stark, wi'
        self._queryRaises(q, AddressNotFoundError)

    def test_PostalAddress_Clackamas(self):
        q = '37798 S Hwy 213, Clackamas, OR 97362'
        geocode = self._query(q)

    def _test_PostalAddress_MultipleMatches(self):
        q = '633 alberta'
        self._queryRaises(q, MultipleMatchingAddressesError)
        try:
            self._query(q)
        except MultipleMatchingAddressesError, e:
            self.assert_(len(e.geocodes) == 2)
        q = '300 main'
        self._queryRaises(q, MultipleMatchingAddressesError)
        try:
            self._query(q)
        except MultipleMatchingAddressesError, e:
            self.assert_(len(e.geocodes) == 8)

    def test_PostalAddress_NoCity(self):
        q = '4408 se stark, or'
        geocode = self._query(q)

    def test_PostalAddress_NoCityOrState(self):
        q = '4408 se stark'
        geocode = self._query(q)

    def test_PostalAddress_NoSuffixOnNumberStreetName(self):
        q = '4550 ne 15'
        geocode = self._query(q)

    def test_PostalAddress_NotFound(self):
        q = '300 bloofy lane, portland, or'
        self._queryRaises(q, AddressNotFoundError)

    def test_PostalAddress_Portland(self):
        q = '633 n alberta st, portland, or, 97217'
        geocode = self._query(q)

    def test_PostalAddress_WithSuffixOnNumberStreetName(self):
        q = '4550 ne 15th'
        geocode = self._query(q)


class Test_An_Existing_Address(unittest.TestCase):
    def test_should_be_found(self):
        q = '4122 NE Sandy'
        geocode = Service(region='portlandor').query(q)


class DontTestMilwaukee(unittest.TestCase):
    A = {
        'milwaukeewi': (
            '0 w hayes ave',
            'x=-87.940407, y=43.05321',
            'x=-87.931137, y=43.101234',
            'x=-87.934399, y=43.047126',
            '125 n milwaukee',
            '125 n milwaukee milwaukee wi',
            '27th and lisbon',
            '27th and lisbon milwaukee',
            '27th and lisbon milwaukee, wi',
            'x=-87.961178, y=43.062993',
            'x=-87.921953, y=43.040791',
            'n 8th st & w juneau ave, milwaukee, wi ',
            '77th and burleigh',
            '2750 lisbon',
            '(-87.976885, 43.059544)',
            'x=-87.946243, y=43.041669',
            '124th and county line',
            '124th and county line wi',
            '5th and center',
            '6th and hadley',
        )
    }


if __name__ == '__main__':
    unittest.main()
