from io import StringIO

DEBUG = False


class Strip:

    #
    #
    #
    def __init__(self):
        self.debug = DEBUG
        self.id = None
        self.footprint = None
        self.bbox = None
        self.centerLat = None
        self.centerLon = None
        self.tileFilesMap = {}  # file file path / data
        self.tileBlockList = []  # list of tileBlock
        # cels map
        # key is ref like: 054623610010_01_P001__0__1-0
        #
        self.cellsMap = None
        # files common to all EoSip
        self.commonContent = None
        # all content
        self.contentList = None
        if self.debug:
            print(" init strip")

    #
    #
    #
    def getInfo(self):
        out = StringIO()
        out.write("Tile group info:\n")
        out.write(" id:%s\n" % self.id)
        out.write(" footprint:%s\n" % self.footprint)
        out.write(" bbox:%s\n" % self.bbox)
        out.write(" centerLat:%s\n" % self.centerLat)
        out.write(" centerLon:%s\n" % self.centerLon)
        out.write(" tileFilesMaps\n" % self.tileFilesMap)
        out.write(" tileBlockList:%s\n" % self.tileBlockList)
        out.write(" cellsMap:%s\n" % self.cellsMap)
        return out.getvalue()

    #
    #
    #
    def numCells(self):
        return len(self.cellsMap)

    #
    #
    #
    def calculateEnveloppe(self):
        allTiles = []
        for cellKey in list(self.cellsMap.keys()):
            for aTile in self.cellsMap[cellKey]:
                allTiles.append(aTile)
        if self.debug:
            print((" getEnveloppe on strip, num tiles:%s" % len(allTiles)))

        northTile = None
        southTile = None
        eastTile = None
        westTile = None

        north = -99999
        for tile in allTiles:
            if self.debug:
                print("test north:%s" % tile.getNorth())
            if tile.getNorth() > north:
                northTile = tile
                north = tile.getNorth()
        if self.debug:
            print(" getEnveloppe on strip ==> north=%s using tile:%s" % (north, northTile.getInfo()))

        south = 99999
        for tile in allTiles:
            if self.debug:
                print("test south:%s" % tile.getSouth())
            if tile.getSouth() < south:
                southTile = tile
                south = tile.getSouth()
        if self.debug:
            print(" getEnveloppe on strip ==> south=%s using tile:%s" % (south, southTile.getInfo()))

        east = -99999
        for tile in allTiles:
            if self.debug:
                print("test east:%s" % tile.getEast())
            if tile.getEast() > east:
                eastTile = tile
                east = tile.getEast()
        if self.debug:
            print(" getEnveloppe on strip ==> east=%s using tile:%s" % (east, eastTile.getInfo()))

        west = 99999
        for tile in allTiles:
            if self.debug:
                print("test west:%s" % tile.getWest())
            if tile.getWest() < west:
                westTile = tile
                west = tile.getWest()
        if self.debug:
            print(" getEnveloppe on strip ==> west=%s using tile:%s" % (west, westTile.getInfo()))

        return "%s %s %s %s %s %s %s %s %s %s" % (north, west, south, west, south, east, north, east, north, west)
