"""Utility class that represent an geographic area, Contains lat, lon
coordinates can:
- calculate center
- calculate envelope
"""
import math

from . import geomHelper

debug = 0


class GeographicArea:
    def __init__(self):
        self.debug = debug
        self.lats = []
        self.lons = []
        self.centerLat = None
        self.centerLon = None
        self.boondingBox = None
        self.isCrossing = None

    def info(self):
        info = "GegraphicArea\n"
        info = "%s num of coords=%s\n" % (info, len(self.lats))
        info = "%s center lat=%s; center lon=%s\n" % (info, self.centerLat, self.centerLon)
        info = "%s boondingBox=%s\n" % (info, self.boondingBox)
        info = "%s isCrossing=%s\n" % (info, self.isCrossing)
        return info

    def addLatLonCoordsString(self, coords):
        if debug != 0:
            print("\naddLatLonCoordsString: %s" % coords)
        toks = coords.split(' ')
        for i in range(len(toks) // 2):
            if debug != 0:
                print(" add[%s]: lat=%s; lon=%s" % (i, float(toks[i * 2]), float(toks[i * 2 + 1])))
            self.lats.append(float(toks[i * 2]))
            self.lons.append(float(toks[i * 2 + 1]))

    def calculateCenter(self):
        self.centerLat, self.centerLon = geomHelper.getLatLngCenter(self.lats, self.lons)
        if debug != 0:
            print("calculateCenter: lat=%s; lon=%s" % (self.centerLat, self.centerLon))

    # test if the footprint is crossing the +/- 180 degree longitude line
    # also in browseImage class
    def testCrossing(self):
        nPair = 1
        numPair = len(self.lats)
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        # test distance in longitudes
        oldLon = None
        for item in range(numPair):
            lon = self.lons[item]
            if oldLon is not None:
                if debug != 0:
                    print(" testCrossing %d, lon=%s, oldLon=%s" % (item, lon, oldLon))
                if float(lon) - float(oldLon) > 180 and float(lon) * float(oldLon) < 0:
                    self.isCrossing = True
                    if debug != 0:
                        print("  @#@#@#@#  CROSSING!")
                    return
            oldLon = lon
        self.isCrossing = False

    # get the boundingBox
    # like in browseImage class, but has 5 coords because is closed
    def calculateBoondingBox(self):
        nPair = 1
        numPair = len(self.lats)

        maxLat = -90
        minLat = 90
        minLon = 180
        maxLon = -180
        for i in range(numPair):
            latn = self.lats[i]
            longn = self.lons[i]

            if latn > maxLat:
                maxLat = latn
            if latn < minLat:
                minLat = latn

            if longn < 0 and self.isCrossing == True:
                longn = longn + 360
                if longn > maxLon:
                    maxLon = longn
                if longn < minLon:
                    minLon = longn
            else:
                if longn > maxLon:
                    maxLon = longn
                if longn < minLon:
                    minLon = longn

            nPair = nPair + 1

        if maxLon > 180:
            maxLon = maxLon - 360
        if self.debug != 0:
            print(" ############ minLat=%s  maxLat=%s   minLon=%s   maxLon=%s" % (minLat, maxLat, minLon, maxLon))
        # we want 4 points: uper left corner, then ccw
        self.boondingBox = "%s %s %s %s %s %s %s %s %s %s" % (maxLat, minLon, minLat, minLon,
                                                              minLat, maxLon, maxLat, maxLon, maxLat, minLon)

    # get the footprint envelope: calculate biggest x/y axe arc-distance from coord[n] to center.
    # also in browseImage class
    # NOT GOOD
    def calculateEnvelope___(self):
        nPair = 1
        numPair = len(self.lats)
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        maxx = 0
        maxy = 0
        fcenterlat = float(self.centerLat)
        fcenterlon = float(self.centerLon)
        for item in range(numPair):
            latn = self.lats[item]
            longn = self.lons[item]
            dy = geomHelper.arcDistanceBetween(fcenterlat, fcenterlon, float(latn), fcenterlon)
            dx = geomHelper.arcDistanceBetween(fcenterlat, fcenterlon, fcenterlat, float(longn))
            if debug != 0:
                print("\n calculateEnvelope 0 coords %d, lat=%s, lon=%s;   dx=%s; dy=%s    maxx=%s; maxy=%s" % (
                nPair, latn, longn, dx, dy, maxx, maxy))
            if dx > maxx:
                maxx = dx
                print("  new maxx")
            if dy > maxy:
                maxy = dy
                print("  new maxy")
            if debug != 0:
                print(" calculateEnvelope 1 coords %d, lat=%s, lon=%s;   dx=%s; dy=%s    maxx=%s; maxy=%s" % (
                nPair, latn, longn, dx, dy, maxx, maxy))
            nPair = nPair + 1

        if debug != 0:
            print(" ==> maxx=%s; maxy=%s" % (maxx, maxy))
        maxLon = math.radians(fcenterlon) + maxx
        minLon = math.radians(fcenterlon) - maxx
        maxLat = math.radians(fcenterlat) - maxy
        minLat = math.radians(fcenterlat) + maxy
        self.boondingBox = "%s %s %s %s %s %s %s %s %s %s" % (
        math.degrees(minLat), math.degrees(minLon), math.degrees(maxLat), math.degrees(minLon),
        math.degrees(maxLat), math.degrees(maxLon), math.degrees(minLat), math.degrees(maxLon),
        math.degrees(minLat), math.degrees(minLon))


if __name__ == '__main__':
    area = GeographicArea()
    area.addLatLonCoordsString(
        '48.99605450 4.00442139 48.96622233 4.00382203 48.96540872 4.09332431 48.99524004 4.09397708 48.99605450 4.00442139')
    area.addLatLonCoordsString(
        '48.99523983 4.09399895 48.96753830 4.09339274 48.96665519 4.18289463 48.99435586 4.18355044 48.99523983 4.09399895')
    area.addLatLonCoordsString(
        '48.99435564 4.18357231 48.96925955 4.18297811 48.96851226 4.25372772 48.99360769 4.25435743 48.99435564 4.18357231')
    area.addLatLonCoordsString(
        '49.05499883 4.00560854 48.99606889 4.00442168 48.99525443 4.09397739 49.05418269 4.09527003 49.05499883 4.00560854')
    area.addLatLonCoordsString(
        '49.05418248 4.09529193 48.99525422 4.09399926 48.99437025 4.18355078 49.05329668 4.18494920 49.05418248 4.09529193')
    area.addLatLonCoordsString(
        '49.05329646 4.18497110 48.99437003 4.18357265 48.99362779 4.25383299 49.05255268 4.25531440 49.05329646 4.18497110')
    area.testCrossing()
    area.calculateCenter()
    area.calculateBoondingBox()
    print(area.info())
