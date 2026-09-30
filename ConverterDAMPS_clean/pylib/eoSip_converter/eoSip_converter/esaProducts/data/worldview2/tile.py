from io import StringIO

import eoSip_converter.geomHelper as geomHelper

debug = False


#
# a tile
#
class Tile:

    #
    #
    #
    def __init__(self):
        self.row = None
        self.col = None
        self.label = None
        self.filename = None
        self.ULLon = None
        self.ULLat = None
        self.URLon = None
        self.URLat = None
        self.LRLon = None
        self.LRLat = None
        self.LLLon = None
        self.LLLat = None
        self.surfaceKms = None
        # to which block is this tile part
        self.tileBlock = None

    #
    #
    #
    def getInfo(self):
        out = StringIO()
        out.write("Tile info:\n")
        out.write(" row:%s\n" % self.row)
        out.write(" col:%s\n" % self.col)
        out.write(" label:%s\n" % self.label)
        out.write(" filename:%s\n" % self.filename)
        out.write(" footprint:%s\n" % self.getFootprint())
        out.write(" tileBlock:%s\n" % self.tileBlock)
        return out.getvalue()

    #
    def getSurfaceKms(self):
        # if self.surfaceKms==None:
        sidea = geomHelper.metersDistanceBetween(float(self.ULLat), float(self.ULLon), float(self.URLat),
                                                 float(self.URLon)) / 1000
        sideb = geomHelper.metersDistanceBetween(float(self.URLat), float(self.URLon), float(self.LRLat),
                                                 float(self.LRLon)) / 1000
        if self.debug:
            print("######### SURFACE:%s and %s" % (sidea, sideb))
        self.surfaceKms = sidea * sideb
        return self.surfaceKms, sidea, sideb

    #
    def getMax(self, a, b, c, d):
        res = a
        if b > a:
            res = b
        if c > res:
            res = c
        if d > res:
            res = d
        return res

    #
    def getMin(self, a, b, c, d):
        res = a
        if b < a:
            res = b
        if c < res:
            res = c
        if d < res:
            res = d
        return res

    #       
    def getFootprint(self):
        footprint = "%s %s" % (self.ULLat, self.ULLon)
        footprint = "%s %s %s" % (footprint, self.LLLat, self.LLLon)
        footprint = "%s %s %s" % (footprint, self.LRLat, self.LRLon)
        footprint = "%s %s %s" % (footprint, self.URLat, self.URLon)
        footprint = "%s %s %s" % (footprint, self.ULLat, self.ULLon)

        # footprint = "%s %s" % (self.ULLat, self.ULLon)
        # footprint = "%s %s %s" % (footprint, self.URLat, self.URLon)
        # footprint = "%s %s %s" % (footprint, self.LRLat, self.LRLon)
        # footprint = "%s %s %s" % (footprint, self.LLLat, self.LLLon)
        # footprint = "%s %s %s" % (footprint, self.ULLat, self.ULLon)
        return footprint

    #
    def getWest(self):
        # if float(self.ULLon) <  float(self.LLLon):
        #    return float(self.ULLon)
        # else:
        #    return float(self.LLLon)
        return self.getMin(float(self.ULLon), float(self.URLon), float(self.LRLon), float(self.LLLon))

    #
    def getEast(self):
        # if float(self.URLon) >  float(self.LRLon):
        #    return float(self.URLon)
        # else:
        #    return float(self.LRLon)
        return self.getMax(float(self.ULLon), float(self.URLon), float(self.LRLon), float(self.LLLon))

    #
    def getNorth(self):
        # if float(self.ULLat) >  float(self.URLat):
        #    return float(self.ULLat)
        # else:
        #    return float(self.URLat)
        return self.getMax(float(self.ULLat), float(self.URLat), float(self.LRLat), float(self.LLLat))

    #
    def getSouth(self):
        # if float(self.LLLat) <  float(self.LRLat):
        #    return float(self.LLLat)
        # else:
        #    return float(self.LRLat)
        return self.getMin(float(self.ULLat), float(self.URLat), float(self.LRLat), float(self.LLLat))
