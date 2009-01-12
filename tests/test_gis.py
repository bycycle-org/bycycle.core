"""$Id$

Tests for the util.gis module.

Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>

All rights reserved.

TERMS AND CONDITIONS FOR USE, MODIFICATION, DISTRIBUTION

1. The software may be used and modified by individuals for noncommercial, 
private use.

2. The software may not be used for any commercial purpose.

3. The software may not be made available as a service to the public or within 
any organization.

4. The software may not be redistributed.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR 
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON 
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
import unittest
from byCycle.util.gis import *


class TestPointClass(unittest.TestCase):
    def testTuple(self):
        p = Point((-122.0, 45.0))
    
    def testWKTGeometry(self):
        p = Point('point (1 2)')
    
    def testEvalAsTuple(self):
        p = Point("('-122.0', '45.0')")
    
    def testTupleOfStrings(self):
        p = Point(('-122.0', '45.0'))
    
    def testTupleOfFloats(self):
        p = Point((-122.0, 45.0))
        p = Point((-122, 45))
    
    def testClonePoint(self):
        p = Point(Point(x=123, y=45))
    
    def testXYFloat(self):
        p = Point(x=-122.0, y=45.0)
        p = Point(x=-122, y=45)
    
    def testXYString(self):
        p = Point(x='-122', y='45')
    
    def testXYPreferred(self):
        p = Point(x_y='Blarg!', x=-123, y=45)
        self.assertEqual(p.x, -123)
        self.assertEqual(p.y, 45)
    
    def testNoArgs(self):
        p = Point()
        self.assertEqual(p.x, None)
        self.assertEqual(p.y, None)


class TestImportWKTGeometry(unittest.TestCase):
    def testImportLinestring(self):
        def checkPoints(lPoints):
            self.assertEqual(lPoints[0].x, 1)
            self.assertEqual(lPoints[0].y, 2)
            self.assertEqual(lPoints[1].x, 2)
            self.assertEqual(lPoints[1].y, 2)
            self.assertEqual(lPoints[2].x, 3)
            self.assertEqual(lPoints[2].y, 2)
        sPoints = 'linestring (1 2,2 2,3 2)'
        lPoints = importWktGeometry(sPoints)
        checkPoints(lPoints)
        sPoints = 'LINESTRING(1 2,2 2,3 2)'
        lPoints = importWktGeometry(sPoints)
        checkPoints(lPoints)
        
    def testImportPoint(self):
        def checkPoint(point):
            self.assertEqual(point.x, 1)
            self.assertEqual(point.y, 2)
        sPoint = 'point (1 2)'
        point = importWktGeometry(sPoint)
        checkPoint(point)
        sPoint = 'POINT(1 2)'
        point = importWktGeometry(sPoint)
        checkPoint(point)
