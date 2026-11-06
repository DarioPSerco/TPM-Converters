import inspect
import os
from io import StringIO

from eoSip_converter.serviceClients.countryResolverStdaClient import CountryResolverStdaClient
from eoSip_converter.serviceClients.luzResolverStdaClient import LuzResolverStdaClient
from eoSip_converter.serviceClients.townResolverStdaClient import TownResolverStdaClient

#
DEBUG = False


#
# a block of nx * ny tiles
#
class TileBlock:

    #
    # tile index starts at 1
    #
    def __init__(self):
        self.debug = DEBUG
        self.id = -1
        self.tiles = {}
        self.rowSize = {}
        self.maxRows = 0
        self.maxCols = 0
        #
        self.order = None
        self.numInOrder = None
        self.path = None
        self.start = None
        self.stop = None
        self.distance = None
        self.cloudCover = None
        self.LuzId = None
        self.iso = None
        self.country = None
        self.town = None
        self.LuzResponse = None
        #
        self.north = None
        self.south = None
        self.east = None
        self.west = None

        # the 3x3 groupped cells
        self.cellsMap = None

        # THE COMMON FILES
        self.commonContent = None

        self.browseFilename = None

    #
    #
    #
    def getInfo(self):
        out = StringIO()
        out.write("Tile group info:\n")
        out.write(" id:%s\n" % self.id)
        out.write(" path:%s\n" % self.path)
        out.write(" rowSize:%s\n" % self.rowSize)
        out.write(" maxRows:%s\n" % self.maxRows)
        out.write(" maxCols:%s\n" % self.maxCols)
        out.write(" tiles:%s\n" % self.tiles)
        out.write(" enveloppe:%s\n" % self.getEnveloppe())

        allFootprints = StringIO()
        for aTileKey in list(self.tiles.keys()):
            if self.debug:
                print(" @@@@@@@@@@@@@@@@@@@@@@@ doing tile:%s" % aTileKey)
            if len(allFootprints.getvalue()) > 0:
                allFootprints.write('\n')
            allFootprints.write(self.tiles[aTileKey].getFootprint())
        out.write(" all footprint:%s\n" % allFootprints.getvalue())
        out.write(" country:%s\n" % self.country)
        out.write(" town:%s\n" % self.town)
        out.write(" LuzId:%s\n" % self.LuzId)
        out.write(" LuzResponse:%s\n" % self.LuzResponse)
        return out.getvalue()

    #
    def size(self):
        return len(self.tiles)

    #
    def addTile(self, tile, col, row):
        tile.row = row
        tile.col = col
        # adjust maxRows/maxCols
        if self.maxRows < row:
            self.maxRows = row
        if self.maxCols < col:
            self.maxCols = col
        # adjust rowSize
        aRowSize = 0
        if "%s" % row in self.rowSize:
            aRowSize = self.rowSize[("%s" % row)]
            if self.debug:
                print("    add tile: aRowSize exists:%s" % aRowSize)
        else:
            if self.debug:
                print("    add tile: aRowSize doesnt exist")

        newSize = aRowSize
        if col > aRowSize:
            self.rowSize[("%s" % row)] = col
            newSize = col
            if self.debug:
                print("    add tile: aRowSize bigger:%s type:%s" % (col, type(col)))
        else:
            if self.debug:
                print("    add tile: aRowSize not bigger")
        #
        self.tiles['%s-%s' % (col, row)] = tile
        tile.label = '%s-%s' % (col, row)
        if self.debug:
            print("    TILE_BLOCK: added tile: col=%s row=%s  rowSize=%s; maxRows=%s  maxCols=%s" % (
            col, row, newSize, self.maxRows, self.maxCols))

    #
    def getNumberOfRow(self):
        len(list(self.rowSize.keys()))

    #
    def getRowNumTiles(self, row):
        num = 0
        for key in list(self.tiles.keys()):
            # print " getRowNumTiles row=%s key=%s" % (row, key)
            acol = key.split('-')[0]
            arow = key.split('-')[1]
            if arow == "%s" % row:
                num = num + 1
        return num

    #
    def getRowSize(self, row):
        return self.rowSize["%s" % row]

    #
    def getTile(self, col, row):
        if "%s-%s" % (col, row) in self.tiles:
            return self.tiles["%s-%s" % (col, row)]
        else:
            raise Exception("tile not found: col=%s row=%s" % (col, row))

    #
    def getAllTilesFilePath(self):
        allTilesPath = []
        for item in self.tiles.values():
            allTilesPath.append(item.filename)
        return allTilesPath

    #
    #
    #
    def calculateEnveloppe(self):

        northTile = None
        southTile = None
        eastTile = None
        westTile = None

        north = -99999
        for tile in list(self.tiles.values()):
            if self.debug:
                print("test north:%s" % tile.getNorth())
            if tile.getNorth() > north:
                northTile = tile
                north = tile.getNorth()
        if self.debug:
            print(" ==> north=%s using tile:%s" % (north, northTile.getInfo()))

        south = 99999
        for tile in list(self.tiles.values()):
            if self.debug:
                print("test south:%s" % tile.getSouth())
            if tile.getSouth() < south:
                southTile = tile
                south = tile.getSouth()
        if self.debug:
            print(" ==> south=%s using tile:%s" % (south, southTile.getInfo()))

        east = -99999
        for tile in list(self.tiles.values()):
            if self.debug:
                print("test east:%s" % tile.getEast())
            if tile.getEast() > east:
                eastTile = tile
                east = tile.getEast()
        if self.debug:
            print(" ==> east=%s using tile:%s" % (east, eastTile.getInfo()))

        west = 99999
        for tile in list(self.tiles.values()):
            if self.debug:
                print("test west:%s" % tile.getWest())
            if tile.getWest() < west:
                westTile = tile
                west = tile.getWest()
        if self.debug:
            print(" ==> west=%s using tile:%s" % (west, westTile.getInfo()))

        self.north = north
        self.south = south
        self.east = east
        self.west = west

        # os._exit(1)

    #
    #
    #
    def getEnveloppe(self):
        if self.debug:
            print(" getEnveloppe: id=%d: maxRow=%s" % (self.id, self.maxRows))

        if self.north is None:
            self.calculateEnveloppe()

        return "%s %s %s %s %s %s %s %s %s %s" % (
        self.north, self.west, self.south, self.west, self.south, self.east, self.north, self.east, self.north,
        self.west)

    #
    # resolve country, town, luz
    #
    def computeInfo(self, pInfo):
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

        if 1 == 2:
            # resolve country
            propPath = "%s/../../../ressources/services/countryResolver.props" % currentdir
            cClient = CountryResolverStdaClient(propPath)
            params = []
            params.append(self.getEnveloppe())
            try:
                iso, country = cClient.callWfsService(params)
                self.iso = iso
                self.country = country
                print(" ############### country response: isoi=%s; country=%s" % (iso, country))
            except Exception as e:
                if pInfo is not None:
                    pInfo.addLog("Error getting country:%s" % e.message)
                raise e

            # resolve town
            propPath = "%s/../../../ressources/services/townResolver.props" % currentdir
            tClient = TownResolverStdaClient(propPath)
            params = []
            params.append(self.getEnveloppe())
            try:
                iso, town = tClient.callWfsService(params)
                self.town = town
                print(" ############### town response: iso=%s; town=%s" % (iso, town))
            except Exception as e:
                if pInfo is not None:
                    pInfo.addLog("Error getting town:%s" % e.message)
                raise e

        #
        # resolve luzid
        #
        # if not resolved, use the strip one stored in processInfo.stripEnveloppe
        #
        propPath = "%s/../../../ressources/services/worldviewLuzResolver.props" % currentdir
        lClient = LuzResolverStdaClient(propPath)
        params = []
        env = self.getEnveloppe()
        params.append(env)
        if pInfo is not None:
            pInfo.addLog("getting luz for enveloppe:%s" % env)
        try:
            luzId, town, country = lClient.callWfsService(params)
            self.LuzId = luzId
            self.country = country
            self.town = town
            self.LuzResponse = "luzId=%s; town=%s; country=%s" % (luzId, town, country)
            print(" ############### luz response: luzId=%s; town=%s; country=%s" % (luzId, town, country))
            if pInfo is not None:
                pInfo.addLog("luz response 0: luzId=%s; town=%s; country=%s" % (luzId, town, country))
        except Exception as e:
            if pInfo is not None and pInfo.stripEnveloppe is not None:
                pInfo.addLog("Error getting cell luz 0:%s. Try strip enveloppe:%s" % (e.message, pInfo.stripEnveloppe))
                params = []
                params.append(pInfo.stripEnveloppe)
                try:
                    luzId, town, country = lClient.callWfsService(params)
                    self.LuzId = luzId
                    self.country = country
                    self.town = town
                    self.LuzResponse = "luzId=%s; town=%s; country=%s" % (luzId, town, country)
                    print(" ############### luz response: luzId=%s; town=%s; country=%s" % (luzId, town, country))
                    pInfo.addLog("luz response 1: luzId=%s; town=%s; country=%s" % (luzId, town, country))
                except Exception as e:
                    pInfo.addLog("Error getting cell luz 1:%s" % e.message)
                    # raise (e)
                    self.LuzId = 'Not-Resolved'
                    self.country = 'Not-Resolved'
                    self.town = 'Not-Resolved'

            else:
                # raise(e)
                self.LuzId = 'Not-Resolved'
                self.country = 'Not-Resolved'
                self.town = 'Not-Resolved'

    #
    #
    #
    def getCenter(self):
        pass
