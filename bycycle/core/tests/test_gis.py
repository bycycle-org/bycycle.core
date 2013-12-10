import unittest
from bycycle.core.util.gis import *


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
