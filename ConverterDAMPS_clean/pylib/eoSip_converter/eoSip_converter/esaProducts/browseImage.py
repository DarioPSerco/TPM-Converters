# -*- coding: cp1252 -*-
#
# utility class used for single products: footprint
# - reverse
# - calculate center
# - test CCW or CW
#
#
#

import math
import sys

import eoSip_converter.esaProducts.formatUtils as formatUtils
import eoSip_converter.geomHelper as geomHelper
from eoSip_converter.geom import vector2D
from eoSip_converter.utils.coordinates import GeodeticCoordinate

debug = 0


class BrowseImage(object):
    sourcePath = None  # browse source path
    footprint = None  # footprint is: 'lat long '...
    origFootprint = None
    boondingBox = None
    centerLat = None
    centerLon = None
    origCenterLat = None
    origCenterLon = None
    colRowList = None  # colrowlist is: 'x y '...
    origColRowList = None
    num_reverseFootprint = 0
    num_reverseColRowList = 0
    isSSW = None
    isClosed = None
    isCrossing = None  # cross +-180 longitude
    valid = True

    def wrapLongitude(self, longStr):
        lon = float(longStr)
        if lon > 180 or lon < -180:
            # print " wrapLongitude str=%s; float=%s" % (longStr, l)
            lon += 180
            # print "    wrapLongitude: l1 = %s" % (l)
            r = lon % 360
            # print "    wrapLongitude: l1=%s; r=%s" % (l, r)
            if lon > 360:
                # print "    wrapLongitude: res1 = %s" % (-180 + r)
                return -180 + r
            else:
                # print "    wrapLongitude: res2 = %s" % (r - 180)
                return r - 180
        else:
            # print "    wrapLongitude: return unchanged"
            return longStr

    def __init__(self):
        self.debug = debug
        pass

    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    def getDebug(self):
        return self.debug

    def setSourcePath(self, p):
        self.sourcePath = p

    def getSourcePath(self):
        return self.sourcePath

    def setFootprint(self, f):
        self.origFootprint = f
        # wrap longitude
        newF = ''
        toks = f.split(' ')
        numPair = int(len(toks) // 2)
        n = 0
        for item in range(numPair):
            lat = toks[(item * 2)]
            lon = self.wrapLongitude(toks[(item * 2) + 1])
            if self.debug != 0:
                print(" setFootprint: pair[%s] lat=%s; lon=%s" % (n, lat, lon))
            if len(newF) > 0:
                newF += ' '
            newF += "%s %s" % (lat, lon)
            n += 1
        if self.debug != 0:
            print(" original footprint ='%s'" % f)
            print(" wrapped  footprint ='%s'" % newF)

        self.footprint = newF
        self.testIsClosed()
        self.testIsCCW()

    def footptintChanged(self):
        return self.origFootprint != self.footprint

    def setCenter(self, lat, lon):
        self.origCenterLat = lat
        self.origCenterLat = lon
        self.centerLat = lat
        self.centerLon = lon

    def getCenter(self):
        """BEWARE: return string, not float"""
        return self.centerLat, self.centerLon

    def setColRowList(self, cr):
        self.colRowList = cr
        self.origColRowList = cr

    def getFootprint(self):
        return self.footprint

    def getBoundingBox(self):
        return self.boondingBox

    def getColRowList(self):
        return self.colRowList

    def reverse(self):
        self.reverseFootprint()
        self.reverseColRowList()

    def makeThumbnail(self, path, reducePercent, minDim=None):
        return "makeThumbnail: to be implemented"

    def testCrossing(self):
        """
        Test if the footprint is crossing the +/- 180 degree longitude
        line
        """
        if self.footprint == None:
            return
        toks = self.footprint.split(" ")
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        # test distance in longitudes
        oldLon = None
        for item in range(numPair):
            lon = toks[(item * 2) + 1]
            if oldLon is not None:
                if self.debug != 0:
                    print("testCrossing %d, lon=%s, oldLon=%s" % (item, lon, oldLon))
                if float(lon) - float(oldLon) > 180 and float(lon) * float(oldLon) < 0:
                    self.isCrossing = True
                    if self.debug != 0:
                        print("@#@#@#@#  CROSSING!")
                    return
            oldLon = lon
        self.isCrossing = False

    #
    # get the boundingBox
    #
    def calculateBoondingBox(self, calculateCenter=True):
        if self.footprint == None:
            return

        if calculateCenter and (self.centerLat == None or self.centerLon == None):
            self.calculateCenter()

        self.testCrossing()

        toks = self.footprint.split(" ")
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print(" calculateEnvelope isCrossing=%s" % self.isCrossing)

        maxLat = -90
        minLat = 90
        minLon = 180
        maxLon = -180
        for item in range(numPair):
            latn = float(toks[item * 2])
            longn = float(toks[item * 2 + 1])

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

        if maxLon > 180:
            maxLon = maxLon - 360
        if self.debug != 0:
            print("############ minLat=%s  maxLat=%s   minLon=%s   maxLon=%s" % (minLat, maxLat, minLon, maxLon))

        # we want 4 points: uper left corner, then ccw
        self.boondingBox = "%s %s %s %s %s %s %s %s" % (maxLat, minLon, minLat, minLon,
                                                        minLat, maxLon, maxLat, maxLon)

    # Added specifically for Planetscope
    def calculateCenterFromBoundingBox(self):
        if self.boondingBox is None:
            raise Exception("boundingbox is None")
        toks=self.boondingBox.split(" ")

        if len(toks)==8:
            alat, alon = geomHelper.getIntermediatePoint(float(toks[0]), float(toks[1]), float(toks[4]), float(toks[5]), 0.5)
            alat1, alon1 = geomHelper.getIntermediatePoint(float(toks[2]), float(toks[3]), float(toks[6]), float(toks[7]), 0.5)
            self.centerLat, self.centerLon = geomHelper.getIntermediatePoint(alat, alon, alat1, alon1, 0.5)
            self.centerLat = formatUtils.EEEtoNumber("%s" % self.centerLat)
            self.centerLon = formatUtils.EEEtoNumber("%s" % self.centerLon)
        else:
            raise Exception("bounding box has not 8 tokens but %s:%s" % (len(toks), self.boondingBox))

        return self.centerLat, self.centerLon

    #
    # get the footprint center: use the first and middle point to do it
    #
    def calculateCenter(self):
        # get the first and middle footprint coords
        toks = self.footprint.split(" ")
        # print "2eme coord: lat=%s lon=%s" % (toks[(len(toks)//2)-1], toks[(len(toks)//2)] )
        # self.centerLat, self.centerLon = geomHelper.coordinateBetween(float(toks[0]), float(toks[1]), float(toks[(len(toks)//2)-1]), float(toks[(len(toks)//2)]))
        # print "@@@@@@@@@@@@@@@@@@@@@@@calculateCenter 0:%s  %s" % (self.centerLat,self.centerLon)
        # self.centerLat=formatUtils.EEEtoNumber("%s" % self.centerLat)
        # self.centerLon=formatUtils.EEEtoNumber("%s" % self.centerLon)
        # print "@@@@@@@@@@@@@@@@@@@@@@@calculateCenter 1:%s  %s" % (self.centerLat,self.centerLon)

        # new:
        if len(toks) == 10:
            alat, alon = geomHelper.getIntermediatePoint(
                float(toks[0]), float(toks[1]),
                float(toks[int(len(toks) // 2) - 1]),
                float(toks[int(len(toks) // 2)]),
                0.5
            )
            # print "@@@@@@@@@@@@@@@@@@@@@@@getIntermediatePoint 0:%s  %s" % (alat, alon)

            alat1, alon1 = geomHelper.getIntermediatePoint(
                float(toks[2]), float(toks[3]),
                float(toks[int(len(toks) // 2) + 1]),
                float(toks[int(len(toks) // 2) + 2]),
                0.5
            )
            # print "@@@@@@@@@@@@@@@@@@@@@@@getIntermediatePoint 1:%s  %s" % (alat1, alon1)

            self.centerLat, self.centerLon = geomHelper.getIntermediatePoint(alat, alon, alat1, alon1, 0.5)
            # print "@@@@@@@@@@@@@@@@@@@@@@@getIntermediatePoint 2:%s  %s" % (self.centerLat, self.centerLon)
            self.centerLat = formatUtils.EEEtoNumber("%s" % self.centerLat)
            self.centerLon = formatUtils.EEEtoNumber("%s" % self.centerLon)
        else:
            raise Exception("footprint has not 10 tokens but %d:%s" % (len(toks), self.footprint))

        return self.centerLat, self.centerLon

    #
    #
    #
    def reverseFootprint(self):
        if self.footprint == None:
            return
        else:
            toks = self.footprint.split(" ")
            ccw = ""
            nPair = 1
            numPair = len(toks) // 2
            if self.debug != 0:
                print(" numPair=%s" % numPair)
            for item in range(numPair):
                if self.debug != 0:
                    print(" pair[%d]:%d:" % (nPair - 1, (numPair - nPair) * 2))
                if len(ccw) > 0:
                    ccw = "%s " % ccw
                ccw = "%s%s %s" % (ccw, toks[(numPair - nPair) * 2], toks[(numPair - nPair) * 2 + 1])
                nPair = nPair + 1
            self.footprint = ccw
            if self.colRowList is not None:  # if there is no colRowList, we don't care about being out of sync
                self.num_reverseFootprint = self.num_reverseFootprint + 1

            self.testIsCCW()
            return ccw

    #
    #
    #
    def reverseSomeFootprint(self, aFootprint):
        toks = aFootprint.split(" ")
        ccw = ""
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        for item in range(numPair):
            if self.debug != 0:
                print(" pair[%d]:%d:" % (nPair - 1, (numPair - nPair) * 2))
            if len(ccw) > 0:
                ccw = "%s " % ccw
            ccw = "%s%s %s" % (ccw, toks[(numPair - nPair) * 2], toks[(numPair - nPair) * 2 + 1])
            nPair = nPair + 1
        return ccw

    #
    # build the colrowlist based on frames durations and image width + height
    #
    def buildDefaultColRowListFromDurations(self, width, height, durations, totalDuration, orbitDirection=None,
                                            footprint=None):
        if self.debug != 0:
            print("buildDefaultColRowListFromDurations: width=%s, height=%s, durations=%s, totalDuration=%s, orbitDirection=%s" % (
                width, height, durations, totalDuration, orbitDirection))
            print("buildDefaultColRowListFromDurations: footprint=%s" % footprint)
        w = width - 1
        h = height - 1
        numPair = len(durations)
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        colrowlist = ''
        actualDuration = 0
        resultDown = ''
        yPixelList = []
        for item in range(numPair):
            actualDuration = actualDuration + durations[item]
            ratio = actualDuration / totalDuration
            yPixel = int(h * ratio)
            yPixelList.append(yPixel)
            if self.debug != 0:
                print(" doing pair=%s; duration=%s; actualDuration=%s" % (item, durations[item], actualDuration))
                print(" doing down pair=%s; ratio=%s; ====>yPixel=%s" % (item, ratio, yPixel))
            if len(resultDown) > 0:
                resultDown = "%s " % resultDown
            # resultDown="%s[d%s]0 %s" % (resultDown, item, yPixel)
            resultDown = "%s0 %s" % (resultDown, yPixel)

        if self.debug != 0:
            print(" buildDefaultColRowListFromDurations: resultDown=%s" % resultDown)

        n = 0
        resultUp = ''
        firstUp = 'dont have firstUp colrow'
        for item in reversed(yPixelList):
            print(" doing up pair=%s; ====>yPixel=%s" % (item, item))
            if len(resultUp) > 0:
                resultUp = "%s " % resultUp
            # resultUp="%s[u%s]%s %s" % (resultUp, n, w, item)
            resultUp = "%s%s %s" % (resultUp, w, item)
            # memorize first
            if n == 0:
                firstUp = "%s %s" % (w, item)
            n = n + 1

        if self.debug != 0:
            print(" buildDefaultColRowListFromDurations: resultUp=%s" % resultUp)

        # ascending or descending?
        if orbitDirection != None:
            if orbitDirection[0] == 'A':
                result = "%s %s 0 0 0 %s %s" % (resultUp, width, resultDown, firstUp)
                if self.debug != 0:
                    print(" buildDefaultColRowListFromDurations: ascending result:%s" % result)
            elif orbitDirection[0] == 'D':
                result = "0 0 %s %s %s 0 0 0" % (resultDown, resultUp, width)
                if self.debug != 0:
                    print(" buildDefaultColRowListFromDurations: descending result=%s" % result)
            else:
                raise Exception("strange orbit direction:%s" % orbitDirection)

        # check agains footprint if any
        if footprint is not None:
            toks1 = footprint.split(" ")
            toks2 = result.split(" ")
            footprintPair = len(toks1) // 2
            colrowlistPair = len(toks2) // 2
            if footprintPair != colrowlistPair:
                raise Exception(
                    "number of pair in colrowlist differ from footprint: %s VS %s" % (footprintPair, colrowlistPair))
        else:
            if self.debug != 0:
                print(" buildDefaultColRowListFromDurations: can not check agains footprint: no footprint set")

        return result

    #
    #
    #
    def reverseColRowList(self, aColRowList=None):
        reverseOther = False
        if aColRowList == None:
            if self.colRowList == None:
                raise Exception("no colrowlist")
            else:
                if self.debug != 0:
                    print(" reverseColRowList on self colrowlist")
                aColRowList = self.colRowList
        else:
            reverseOther = True
            if self.debug != 0:
                print(" reverseColRowList on passed value")

        toks = aColRowList.split(" ")
        ccw = ""
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print(" numPair=%s" % numPair)
        for item in range(numPair):
            if self.debug != 0:
                print(" pair[%d]:%d:" % (nPair - 1, (numPair - nPair) * 2))
            if len(ccw) > 0:
                ccw = "%s " % ccw
            ccw = "%s%s %s" % (ccw, toks[(numPair - nPair) * 2], toks[(numPair - nPair) * 2 + 1])
            nPair = nPair + 1
        if not reverseOther == None:
            self.colRowList = ccw
            self.num_reverseColRowList = self.num_reverseColRowList + 1
            if self.debug != 0:
                print(" reverseColRowList self value; result=%s" % ccw)
        else:
            if self.debug != 0:
                print(" reverseColRowList on passed value; result=%s" % ccw)
        return ccw

    #
    #
    #
    def testIsClosed(self):
        isClosed = True
        toks = self.footprint.split(' ')
        n = len(toks)
        if n >= 4:
            if toks[0] == toks[n - 2] and toks[1] == toks[n - 1]:
                self.isClosed = True
            else:
                self.isClosed = False

        else:
            raise Exception("footprint has to few pairs:%s" % n)

    #
    # test if the footprint in CCW or CW. By somming the sides angles
    #
    def testIsCCW(self):
        toks = self.footprint.split(' ')
        f = []
        totAngle = 0
        for item in toks:
            f.append(float(item))
        for i in range((len(f) // 2) - 1):
            n = i * 2
            # print "\n\nn:%s  len(f):%d" % (n, len(f))
            y1 = f[n]
            x1 = f[n + 1]
            nn = n + 2
            if nn >= len(
                    f):  # we come back to the first point, so use the next one to build the second angle?? normally should never be the case because it's the next test the good one
                if self.debug != 0:
                    print("0 nn=%s>%s so set to:%s" % (nn, len(f), nn - len(f)))
                nn = nn - len(f) + 2
            y2 = f[nn]
            x2 = f[nn + 1]
            nn = nn + 2
            if nn >= len(
                    f):  # this should be the good test: we come back to the first point, so use the next one to build the second angle
                if self.debug != 0:
                    print("1 nn=%s>%s so set to:%s" % (nn, len(f), nn - len(f) + 2))
                nn = nn - len(f) + 2
            y3 = f[nn]
            x3 = f[nn + 1]
            if self.debug != 0:
                print("do point[%s]:%s %s vs %s %s vs %s %s " % (n, x1, y1, x2, y2, x3, y3))
            v1 = vector2D.Vec2d(x2 - x1, y2 - y1)
            v2 = vector2D.Vec2d(x3 - x2, y3 - y2)
            # print "\nv1=%s" % v1
            # print "v2=%s" % v2
            angle = v2.get_angle_between(v1)
            if self.debug != 0:
                print(">>>>>>>>>>>angle:%f" % v2.get_angle_between(v1))
            totAngle = totAngle + angle

        if self.debug != 0:
            print("total angle=%s" % totAngle)
        if totAngle < 0:
            self.isCCW = True
        else:
            self.isCCW = False
        return self.isCCW

    #
    #
    #
    def getIsCCW(self):
        return self.isCCW

    #
    #
    #
    def getIsClosed(self):
        return self.isClosed

    #
    # test if a footprint has his first point on the top left.
    #
    def testFirstPointTopLeft(self):
        # print browse.info()
        toks = self.footprint.split(" ")
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print("\n testFirstPointTopLeft numPair=%s" % numPair)

        # test will be: angle from point 0 and scene center is >= 90 and <= 180
        fLat = float(toks[0])
        fLon = float(toks[1])

        if self.centerLon is None:
            self.calculateCenter()

        print((" ############## self.centerLon:%s" % self.centerLon))

        vecFromCenter = vector2D.Vec2d(fLon - float(self.centerLon), fLat - float(self.centerLat))
        angle = vecFromCenter.get_angle()
        if self.debug != 0:
            print(" testFirstPointTopLeft vecFromCenter=%s" % vecFromCenter)
            print(" testFirstPointTopLeft vecFromCenter angle=%s" % angle)

        if angle >= 90 and angle <= 180:
            if self.debug != 0:
                print(" testFirstPointTopLeft is top left")
            return True
        else:
            if self.debug != 0:
                print(" testFirstPointTopLeft is NOT top left")
            return False

    #
    # test if a footprint has his first point on the bottom right.
    #
    def testFirstPointBottomRight(self):
        # print browse.info()
        toks = self.footprint.split(" ")
        nPair = 1
        numPair = len(toks) // 2
        if self.debug != 0:
            print("\n testFirstPointBottomRight numPair=%s" % numPair)

        # test will be: angle from point 0 and scene center is >= 270 and <= 360
        fLat = float(toks[0])
        fLon = float(toks[1])

        if self.centerLon is None:
            self.calculateCenter()

        vecFromCenter = vector2D.Vec2d(fLon - float(self.centerLon), fLat - float(self.centerLat))
        angle = vecFromCenter.get_angle()
        if self.debug != 0:
            print(" testFirstPointBottomRight vecFromCenter=%s" % vecFromCenter)
            print(" testFirstPointBottomRight vecFromCenter angle=%s" % angle)

        if angle >= 270 and angle <= 360:
            if self.debug != 0:
                print(" testFirstPointBottomRight is bottom right")
            return True
        else:
            if self.debug != 0:
                print(" testFirstPointBottomRight is NOT bottom right")
            return False

    #
    # return a footprint that start at top left corner
    # modify it if needed
    #
    # ONLY for 5 points footprint
    #
    def getTopLeftFootprint(self):
        # print browse.info()
        if self.testFirstPointTopLeft():  # already top left
            if self.debug != 0:
                print(" getTopLeftFootprint: is alread ok")
            return self.footprint
        else:  # modify it
            if self.debug != 0:
                print(" getTopLeftFootprint: modify it")
            if not self.isClosed:
                raise Exception("footprint has to be closed:%s" % self.footprint)
            aFootprint = " ".join(self.footprint.split(' ')[0:-2])
            aLongFootprint = "%s %s" % (aFootprint, aFootprint)
            if self.debug != 0:
                print(" getTopLeftFootprint: aLongFootprint:%s" % aLongFootprint)

            n = self.findPointTopLeft()
            if self.debug != 0:
                print(" getTopLeftFootprint: top left is at point index:%s" % n)
            result = ""
            toks = aLongFootprint.split(' ')
            n = n * 2
            for i in range(8):
                if len(result) > 0:
                    result = "%s " % result
                result = "%s%s" % (result, toks[n + i])
                if self.debug != 0:
                    print(" getTopLeftFootprint: result[%s]=%s" % (i, result))
            result = "%s %s %s" % (result, toks[n], toks[n + 1])

            if self.debug != 0:
                print(" getTopLeftFootprint: final result=%s" % result)
            return result

    #
    # find the index of the point at top left corner
    # in EoSip footprint (5 points, closed). We expect 0 is top left for descending
    # in EoSip footprint (5 points, closed). We expect 0 is bottom right for ascending
    #
    def findPointTopLeft(self):
        # print browse.info()
        # remove duplicated point if any
        aFootprint = self.footprint
        if self.isClosed:
            aFootprint = " ".join(self.footprint.split(' ')[0:-2])

        toks = aFootprint.split(" ")
        numPair = len(toks) // 2
        n = 0
        topLeftIndex = -1
        if self.debug != 0:
            print("\n findPointTopLeft test aFootprint:%s" % aFootprint)
        for item in range(numPair):
            # test will be: angle from point 0 and scene center is <=0 and >= -90
            fLat = float(toks[(item * 2)])
            fLon = float(toks[(item * 2) + 1])
            if self.debug != 0:
                print(" findPointTopLeft test point[%s]: lat=%s; lon=%s" % (n, fLat, fLon))

            if self.centerLon is None:
                self.calculateCenter()

            vecFromCenter = vector2D.Vec2d(fLon - float(self.centerLon), fLat - float(self.centerLat))
            angle = vecFromCenter.get_angle()
            if self.debug != 0:
                print(" findPointTopLeft vecFromCenter=%s" % vecFromCenter)
                print(" findPointTopLeft vecFromCenter angle=%s" % angle)

            if angle >= 90 and angle <= 180:
                topLeftIndex = n
                if self.debug != 0:
                    print(" findPointTopLeft is top left")
            else:
                if self.debug != 0:
                    print(" findPointTopLeft is NOT top left")

            n = n + 1

        return topLeftIndex

    #
    #
    #
    def info(self):
        info = "browseImage\n"
        info = "%s source file path=%s\n" % (info, self.sourcePath)
        info = "%s original footprint=%s\n" % (info, self.origFootprint)
        infp = "%s original colRowList=%s\n" % (info, self.origColRowList)
        info = "%s footprint=%s\n" % (info, self.footprint)
        info = "%s colRowList=%s\n" % (info, self.colRowList)
        info = "%s center: lat=%s; lon=%s\n" % (info, self.centerLat, self.centerLon)
        info = "%s is CCW=%s\n" % (info, self.isCCW)
        info = "%s is closed=%s\n" % (info, self.isClosed)
        info = "%s boondingBox=%s\n" % (info, self.boondingBox)
        if self.num_reverseColRowList != self.num_reverseFootprint:
            info = "%s ERROR: number of reverse footprint != reverse colRowList: %s vs %s\n" % (
                info, self.num_reverseColRowList, self.num_reverseFootprint)
            self.valid = False
        return info


if __name__ == '__main__':
    browse = BrowseImage()

    FIRST_POINT_NOT_TOP_LEFT = "79.221973 12.940168 78.851969 10.898210 78.460248 12.792972 78.817962 14.826912 79.221973 12.940168"

    CW = "13.237765 105.332170 13.120772 105.867829 12.589489 105.746931 12.706410 105.212384 13.237765 105.332170"
    CCW = "33.4251093094 -112.882289019 32.5686324568 -112.864185549 32.5820537783 -111.319645467 33.4389746971 -111.322751764 33.4251093094 -112.882289019"

    browse.setDebug(1)
    browse.setFootprint(FIRST_POINT_NOT_TOP_LEFT)
    print("FIRST_POINT_NOT_TOP_LEFT is CCW:%s" % browse.testIsCCW())

    browse.calculateCenter()
    print("FIRST_POINT_NOT_TOP_LEFT center:%s" % (browse.getCenter(),))

    # browse.setFootprint(CW)
    # print "CW is CCW:%s"% browse.testIsCCW()

    # browse.calculateBoondingBox()
    browse.testFirstPointTopLeft()

    sys.exit(1)

    # terrasar-x 0
    # browse.setFootprint("27.1734459650249 248.4442893447732 28.5578159746287 248.1582520901816 28.3810557183122 247.0839736194089 27.00026060604 247.404870944124 27.1734459650249 248.4442893447732")

    # will not be wrapped
    # browse.setFootprint("65.6945972889829 25.218532650863 66.1882670105899 24.9594766466951 66.1561630180513 24.5934041477376 65.6627506298779 24.857824242906 65.6945972889829 25.218532650863")

    # will be wrapped
    browse.setFootprint(
        "31.2726540782703 246.4695479607213 32.6556184026144 -246.1900124754795 32.4885027705067 245.0728483836106 31.1055174289434 245.3710307821962 31.2726540782703 246.4695479607213")

    # browse.setFootprint('38.585 31.0654 38.3598 31.0715 38.3642 31.3574 38.5894 31.3523 38.585 31.0654')
    # ikonos case 1 GOOD: 1 2 3 0. 20090721222747_po_2627437_0000000.zip
    # browse.setFootprint('49.2677920584 4.0783061109 49.1493720275 4.0757335716 49.1477702883 4.2357427199 49.2661836565 4.2386976869 49.2677920584 4.0783061109')

    # ikonos case 1 NOT GOOD: 20091106153749_po_2628219_0000000.zip
    # browse.setFootprint('40.0050518137 27.1034009954 40.0050935154 26.9679758147 39.8835050717 26.9680324521 39.8834635483 27.1032181229 40.0050518137 27.1034009954')

    # 5c2
    # browse.setFootprint('48.82396301 2.38980728 48.82440092 2.47906769 48.76546197 2.47967758 48.76502496 2.39052166 48.82396301 2.38980728')

    # footprint:
    # browse.setFootprint('44.024164841 -8.7160768638 43.509325509 -8.9472644009 43.329883991 -8.0379892775 43.842763299 -7.7996230099 44.024164841 -8.7160768638')
    # bounding box
    # browse.setFootprint('44.024164841 -8.9472644009 43.329883991 -8.9472644009 43.329883991 -7.7996230099 44.024164841 -7.7996230099 44.024164841 -8.9472644009')

    # footprint: SP1_OPER_HRV__X__1A_19880831T104313_19880831T104322_000213_0046_0240
    # browse.setFootprint('54.446107562 8.0284732983 53.929378846 7.7665146667 53.793347102 8.6495566753 54.308395891 8.9219220663 54.446107562 8.0284732983')
    # bounding box: SP1_OPER_HRV__X__1A_19880831T104313_19880831T104322_000213_0046_0240
    # browse.setFootprint('54.446107562 7.7665146667 53.793347102 7.7665146667 53.793347102 8.9219220663 54.446107562 8.9219220663 54.446107562 7.7665146667')

    # footprint: SP4_OPER_HRI__I__1B_20070621T095302_20070621T095311_000326_0076_0272:
    # browse.setFootprint('39.12997487 16.06485481 38.604857776 15.895899911 38.499880427 16.568997734 39.024211243 16.742794869 39.12997487 16.06485481')
    # bounding box: SP4_OPER_HRI__I__1B_20070621T095302_20070621T095311_000326_0076_0272:
    # browse.setFootprint('39.12997487 15.895899911 38.499880427 15.895899911 38.499880427 16.742794869 39.12997487 16.742794869 39.12997487 15.895899911')

    # bf:
    # browse.setFootprint('44.8291 33.1096 44.1762 32.9438 44.0111 34.1619 44.6621 34.3406 44.8291 33.1096')
    # c4:
    # browse.setFootprint('66.412445 -20.979864 65.727463 -21.312971 65.586067 -19.664280 66.268730 -19.287031 66.412445 -20.979864')

    lon = 146.0
    b = browse.wrapLongitude(lon)

    lon = 185.0
    b = browse.wrapLongitude(lon)

    lon = -185.0
    b = browse.wrapLongitude(lon)

    lon = 365.0
    b = browse.wrapLongitude(lon)

    lon = 355.0
    b = browse.wrapLongitude(lon)

    # os._exit(1)

    print("\n\nworking on coords:%s" % browse.getFootprint())
    print("")

    browse.calculateCenter()
    browse.calculateBoondingBox()
    print(" testFirstPointTopLeft:%s" % browse.testFirstPointTopLeft())
    # browse.findPointTopLeft()
    print(" top left footprint:%s" % browse.getTopLeftFootprint())
    print(browse.info())

    sys.exit(0)

    browse.setFootprint(
        '40.0050518137 27.1034009954 40.0050935154 26.9679758147 39.8835050717 26.9680324521 39.8834635483 27.1032181229 40.0050518137 27.1034009954')
    print("\n\nworking on coords:%s" % browse.getFootprint())
    print("")

    browse.calculateCenter()
    browse.calculateBoondingBox()
    print(" testFirstPointTopLeft:%s" % browse.testFirstPointTopLeft())
    browse.findPointTopLeft()
    print(" top left footprint:%s" % browse.getTopLeftFootprint())
    print(browse.info())

    fd = open("boundingBox_try_original.txt", "w")
    fd.write(browse.info())
    fd.close()

    sys.exit(0)

    browse.reverse()
    print("\nreversed:")
    print(browse.info())
    print("\n\n\n\n")

    fd = open("boundingBox_try_reverded.txt", "w")
    fd.write(browse.info())
    fd.close()

    sys.exit(0)
    # razvan BI
    # browse.setFootprint('50.875046 -1.722543 51.310780 -0.413662 50.546196 0.213645 50.116253 -1.076558 50.875046 -1.722543')
    # f130:
    # browse.setFootprint('51.107277 -3.388437 51.544346 -2.074867 50.715931 -1.393089 50.284798 -2.687346 51.107277 -3.388437')
    # d79f:
    # browse.setFootprint('66.412445 -20.979864 65.727463 -21.312971 65.586067 -19.664280 66.268730 -19.287031 66.412445 -20.979864')
    # browse.setFootprint("0.43 112.969 -0.421 112.969 -0.421 113.443 0.43 113.443 0.43 112.969")
    # from terrasar-x : more than 180 longitude
    browse.setFootprint(
        "27.1734459650249 248.4442893447732 28.5578159746287 248.1582520901816 28.3810557183122 247.0839736194089 27.00026060604 247.404870944124 27.1734459650249 248.4442893447732")
    browse.calculateCenter()
    browse.calculateBoondingBox()
    print(browse.info())
    fd = open("boundingBox_try.txt", "w")
    fd.write(browse.info())
    fd.close()
    browse.reverse()
    print("\nreversed:")
    print(browse.info())
