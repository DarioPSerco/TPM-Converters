import os
import re
import sys
import time
import traceback

import eoSip_converter.esaProducts.browseImage as browseImage
import eoSip_converter.esaProducts.formatUtils as formatUtils
import eoSip_converter.geomHelper as geomHelper
from eoSip_converter.esaProducts.browseImage import BrowseImage
#
from eoSip_converter.esaProducts.data.worldview2.strip import Strip
from eoSip_converter.esaProducts.data.worldview2.tile import Tile
from eoSip_converter.esaProducts.data.worldview2.tileBlock import TileBlock
from eoSip_converter.esaProducts.sectionIndentedDocument import SectionDocument
from eoSip_converter.fileHelper import FileHelper
from eoSip_converter.xmlHelper import XmlHelper

#
DEBUG = True

# default names
blocksVectorObjectJson = 'blocks_enveloppe'
blockDetailVectorObjectJson = 'block_detail_enveloppe'
cellDetailVectorObjectJson = 'cell_detail_enveloppe'

#
# extend the json file with the current tile
#
JSON_PATTERN = '        {"type":"Feature", "properties":{"order":"ORDER", "country":"COUNTRY", "city":"CITY", "luzId":"LUZID"}, "geometry":{"type":"Polygon", "coordinates":[[PAIR_LONG_VIRGOLA_LAT_VIRGOLA]]}}'


#
# - parse worldview2 product folders
# - read product '^.*_Urban_Atlas_.*$', '^.xml$'; README.TXT + .TIL files
# - group tiles in block of 3 * 3
# - prepare xml files describing the block, ready for the EoSip converter
#
class TileGrouper:
    firstJson = False
    jsonFileHome = '.'

    def __init__(self):
        self.debug = DEBUG
        if self.debug:
            print(" init TileGrouper")

    def setJsonFileHome(self, aPath):
        self.jsonFileHome = aPath

    #
    # parse tile file data
    # return a list of tileBlock
    #
    def parseTileData(self, basePath, aStrip, data, processInfo):
        if self.debug:
            print(" ## parsing TILE data")
        sectionDoc = SectionDocument()
        sectionDoc.setContent(data)

        n = sectionDoc.getSectionLine('tileSizeX*')
        v = sectionDoc.getLineValue(n, None, '=')
        tileSizeX = int(v.replace(' ', '').replace(';', ''))
        if self.debug:
            print("  tileSizeX='%s'" % tileSizeX)

        n = sectionDoc.getSectionLine('tileSizeY*')
        v = sectionDoc.getLineValue(n, None, '=')
        tileSizeY = int(v.replace(' ', '').replace(';', ''))
        if self.debug:
            print("  tileSizeY='%s'" % tileSizeY)

        n = sectionDoc.getSectionLine('numTiles*')
        v = sectionDoc.getLineValue(n, None, '=')
        numTiles = int(v.replace(' ', '').replace(';', ''))
        if self.debug:
            print("  numTiles='%s'" % numTiles)

        numBlocks = int(numTiles / 9)
        numRemainTiles = -1  # numTiles-(numFullProducts*9)
        if self.debug:
            print("  numTiles='%s'" % numTiles)
            print("  numRemainTiles='%s'" % numRemainTiles)

        tileBlock = None
        currentTile = 0
        currentBlock = 0
        blockList = []
        tileInBlock = 0
        rowsInBlock = {}
        lastCol = 0
        lastRow = 0

        topLat = -9999.0
        topLon = -9999.0
        bottomLat = -9999.0
        bottomLon = -9999.0
        orderDistance = -9999.0
        for currentTile in range(numTiles):

            n = sectionDoc.getSectionLine('BEGIN_GROUP = TILE_%s' % (currentTile + 1))
            # print "   section line:%s" % n

            filename = sectionDoc.getLineValue(n + 1, '', '=').replace('"', '').replace(';', '').strip()

            # get real orderId from tile tile name: 13OCT03110656-M2AS_R1C1-053963552010_01_P001.TIF: is the part: 053963552010_01_P001
            realOrderId = filename.split('-')[2]
            realOrderId = realOrderId.split('.')[0]

            # get row and col from tile name
            toks = filename.split('_')
            rc = toks[1].split('-')[0]
            row = rc[1:].split('C')[0]
            col = rc[1:].split('C')[1]
            rowsInBlock[row] = col

            newBlock = False
            if tileInBlock == 0:
                # print "  doint tile %s; empty block: %s" % (currentTile, currentBlock)
                newBlock = True
            if self.debug:
                print("\n\n####\n####\n  starting tile %s" % currentTile)
                print("   this is row:%s; col:%s; tileInBlock:%s; rowsInBlock size:%s" % (
                    row, col, tileInBlock, len(rowsInBlock)))

            if len(list(rowsInBlock.keys())) == 4:
                if self.debug:
                    print(" doint tile %s; block:%s completed; size:%s; numRows:%s\n" % (
                        currentTile, currentBlock, tileBlock.size(), tileBlock.maxRows))
                footprint = tileBlock.getEnveloppe()
                browse = browseImage.BrowseImage()
                browse.setFootprint(footprint)
                centerLat, centerLon = browse.calculateCenter()
                if self.debug:
                    print(" @@@@@@@@@@@@@@@ block11 [%s] center: lart=%s lon=%s" % (currentBlock, centerLat, centerLon))
                    print("####################### will sphericalDistance:%s|%s|%s|%s|" % (
                        type(centerLat), type(centerLon), type(topLat), type(topLon)))
                    print("####################### will sphericalDistance:%s|%s|%s|%s|" % (
                        float(centerLat), float(centerLon), topLat, topLon))
                # in radian
                # block.distance=geomHelper.sphericalDistance(float(centerLat), float(centerLon), topLat, topLon)
                # in kms
                tileBlock.distance = geomHelper.metersDistanceBetween(float(centerLat), float(centerLon), topLat,
                                                                      topLon) / 1000
                # get LUZ info, is like: "LUZ_ID", "COUNTRY", "TOWN"
                # toks = order.split('_')
                # orderId = "%s_%s" % (toks[0], toks[1])
                # block.LuzId, block.country, block.town, block.phone = getOrderLuzInfo(orderId)

                #
                tileBlock.computeInfo(processInfo)
                #

                blockList.append(tileBlock)
                tileInBlock = 0
                rowsInBlock = {}
                newBlock = True

            lastCol = col
            lastRow = row

            if newBlock:
                newBlock = False
                currentBlock = currentBlock + 1
                if self.debug:
                    print("\n   doing tile %s; filename: %s" % (currentTile, filename))
                    print("\n   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  new block created:%s" % currentBlock)
                tileBlock = TileBlock()
                if self.debug:
                    print("    TILE_BLOCK: create tile; currentBlock:%s" % currentBlock)
                tileBlock.path = basePath
                tileBlock.id = currentBlock
                # block.start = collectionStart
                # block.stop = collectionStop
                # block.cloudCover = cloudCover
                # block.numRows=3
                tileBlock.order = realOrderId
                # block.path = folder
            else:
                if self.debug:
                    print("\n doint tile %s; filename: %s" % (currentTile, filename))

            ULLon = sectionDoc.getLineValue(n + 10, '', '=').replace('"', '').replace(';', '').strip()
            ULLat = sectionDoc.getLineValue(n + 11, '', '=').replace('"', '').replace(';', '').strip()
            URLon = sectionDoc.getLineValue(n + 12, '', '=').replace('"', '').replace(';', '').strip()
            URLat = sectionDoc.getLineValue(n + 13, '', '=').replace('"', '').replace(';', '').strip()
            LRLon = sectionDoc.getLineValue(n + 14, '', '=').replace('"', '').replace(';', '').strip()
            LRLat = sectionDoc.getLineValue(n + 15, '', '=').replace('"', '').replace(';', '').strip()
            LLLon = sectionDoc.getLineValue(n + 16, '', '=').replace('"', '').replace(';', '').strip()
            LLLat = sectionDoc.getLineValue(n + 17, '', '=').replace('"', '').replace(';', '').strip()

            # get center top lat lon
            if col == '2':
                bottomLat, bottomLon = geomHelper.getIntermediatePoint(float(LLLat), float(LLLon), float(LRLat),
                                                                       float(LRLon), .5)
                if topLat == -9999.0:
                    if self.debug:
                        print("####################### will getIntermediatePoint:%s|%s|%s|%s|" % (
                            float(ULLat), float(ULLon), float(URLat), float(URLon)))
                    topLat, topLon = geomHelper.getIntermediatePoint(float(ULLat), float(ULLon), float(URLat),
                                                                     float(URLon),
                                                                     .5)
                    if self.debug:
                        print("\n @@@@@@@@@@@@@@@ doint tile %s; top center lat:%s lon:%s" % (
                        currentTile, topLat, topLon))

            tile = Tile()
            tile.filename = filename
            tile.ULLon = ULLon
            tile.ULLat = ULLat
            tile.URLon = URLon
            tile.URLat = URLat
            tile.LRLon = LRLon
            tile.LRLat = LRLat
            tile.LLLon = LLLon
            tile.LLLat = LLLat

            tile.tileBlock = tileBlock

            tileBlock.addTile(tile, int(col), int(row) - ((currentBlock - 1) * 3))
            tileInBlock = tileInBlock + 1

        if len(tileBlock.tiles) > 0:
            # do last tileBlock
            footprint = tileBlock.getEnveloppe()
            browse = browseImage.BrowseImage()
            browse.setFootprint(footprint)
            centerLat, centerLon = browse.calculateCenter()
            tileBlock.distance = geomHelper.metersDistanceBetween(float(centerLat), float(centerLon), topLat,
                                                                  topLon) / 1000
            tileBlock.computeInfo(processInfo)
            blockList.append(tileBlock)

        return blockList

    #
    # parse a xxxx_README.TXT file. Like: 13APR03114829-P2AS-054623610010_01_P001_README.TXT
    #
    # contains list of files, + some metadata
    #
    def parseReadmeData(self, basePath, aStrip, tileFileData, processInfo):
        if self.debug:
            print((" ## parseReadmeData; basePath=%s" % basePath))

        #
        # list of files
        #
        inFile = False
        contentList = []
        commonContent = []
        for aLine in tileFileData.split('\n'):
            if len(aLine.strip()) > 0:
                if inFile:
                    if aLine.endswith('";'):
                        contentList.append(aLine[0: -len('";')])
                        if not aLine.endswith('.TIF') and not aLine.endswith('.JPG'):
                            commonContent.append(aLine[0: -len('";')])
                        inFile = False
                    else:
                        contentList.append(aLine)
                        if not aLine.endswith('.TIF') and not aLine.endswith('.JPG'):
                            commonContent.append(aLine)
                if aLine.startswith('fileList = "'):
                    inFile = True
        if self.debug:
            print(" ################## contentList:%s" % contentList)
            print("\n\n ################## commonContent:%s" % commonContent)
        # os._exit(1)

        # put common content in strip, also
        aStrip.commonContent = commonContent
        aStrip.contentList = contentList

        #
        # get metadata
        #
        # start/ stop
        sectionDoc1 = SectionDocument()
        sectionDoc1.setContent(tileFileData)
        n = sectionDoc1.getSectionLine('collectionStart*')
        v = sectionDoc1.getLineValue(n, None, '=')
        collectionStart = v.replace(' ', '').replace(';', '')
        if self.debug:
            print("  collectionStart 0='%s'" % collectionStart)
        collectionStart = formatUtils.removeMsecFromdateString(collectionStart)
        if self.debug:
            print("  collectionStart 1='%s'" % collectionStart)

        n = sectionDoc1.getSectionLine('collectionStop*')
        v = sectionDoc1.getLineValue(n, None, '=')
        collectionStop = v.replace(' ', '').replace(';', '')
        collectionStop = formatUtils.removeMsecFromdateString(collectionStop)
        if self.debug:
            print("  collectionStop='%s'" % collectionStop)

        startDateTime = formatUtils.timeFromDatePatterm(collectionStart)
        stopDateTime = formatUtils.timeFromDatePatterm(collectionStop)
        deltaTime = stopDateTime - startDateTime
        if self.debug:
            print("  startDateTime='%s'; stopDateTime='%s'; dif=%s" % (startDateTime, stopDateTime, deltaTime))

        # scene corners
        n = sectionDoc1.getSectionLine('nwLat*')
        nwLat = sectionDoc1.getLineValue(n, None, '=')[1:-1]
        nwLong = sectionDoc1.getLineValue(n + 1, None, '=')[1:-1]
        seLat = sectionDoc1.getLineValue(n + 2, None, '=')[1:-1]
        seLong = sectionDoc1.getLineValue(n + 3, None, '=')[1:-1]

        footprint = '%s %s' % (nwLat, nwLong)
        footprint = '%s %s %s' % (footprint, nwLat, seLong)
        footprint = '%s %s %s' % (footprint, seLat, seLong)
        footprint = '%s %s %s' % (footprint, seLat, nwLong)
        footprint = '%s %s %s' % (footprint, nwLat, nwLong)
        if self.debug:
            print(("  footprint: %s" % footprint))

        # TIL files
        tileBlockList = None
        for line in tileFileData.split('\n'):
            if line.endswith('.TIL'):
                if self.debug:
                    print(("  tile file: %s" % line))
                if line.find('_MUL/') > 0:
                    if self.debug:
                        print(("  MUL tile file: %s" % line))
                    aPath = "%s/%s_01/%s" % (basePath, aStrip.id, line.strip())
                    fd = open(aPath, 'r')
                    tilData = fd.read()
                    fd.close()
                    aStrip.tileFilesMap[os.path.basename(line.strip())] = tilData

                    tileBlockList = self.parseTileData(basePath, aStrip, tilData, processInfo)
                    if self.debug:
                        print("@@@@@@@@@@@@@@@@@@ tileBlockList: %s" % tileBlockList)

        # display block info
        n = 0
        for aTileBlock in tileBlockList:
            # set common content
            aTileBlock.commonContent = commonContent
            if self.debug:
                print(" tileBlock[%s]: %s" % (n, aTileBlock.getInfo()))

        # output block json for debuging
        # firstJson = True
        fd = open("%s/%s__%s.json" % (self.jsonFileHome, blocksVectorObjectJson, aStrip.id), 'w')
        self.initJson(fd)
        n = 0
        for aTileBlock in tileBlockList:
            if self.debug:
                print(" tileBlock[%s]: %s" % (n, aTileBlock.getInfo()))
            self.extentToJson(fd, aTileBlock.west, aTileBlock.north, aTileBlock.east, aTileBlock.south,
                              "Order:%s; Block:%s" % (aTileBlock.order, aTileBlock.id), aTileBlock.country,
                              aTileBlock.town, "LuzId:%s; maxRows:%s; maxCols:%s; rowSize{}:%s; tilesLabels:%s" % (
                              aTileBlock.LuzId, aTileBlock.maxRows, aTileBlock.maxCols, aTileBlock.rowSize,
                              list(aTileBlock.tiles.keys())))
        fd.flush()
        self.closeJson(fd)
        print((" ==> block of tiles exported as json in:%s/%s__%s.json" % (
        self.jsonFileHome, blocksVectorObjectJson, aStrip.id)))

        # output block tiles json for debuging
        n = 0
        for aTileBlock in tileBlockList:
            # firstJson = True
            fd = open("%s/%s__%s__block-%s.json" % (self.jsonFileHome, blockDetailVectorObjectJson, aStrip.id, n), 'w')
            self.initJson(fd)
            for aTile in list(aTileBlock.tiles.values()):
                self.extentToJson(fd, aTile.getWest(), aTile.getNorth(), aTile.getEast(), aTile.getSouth(),
                                  aTile.filename, "Col:%s" % aTile.col, "Row:%s" % aTile.row, "Label:%s" % aTile.label)
            fd.flush()
            self.closeJson(fd)
            n += 1

        #
        aStrip.footprint = footprint
        browse = BrowseImage()
        browse.setFootprint(footprint)
        browse.calculateBoondingBox()
        aStrip.bbox = browse.boondingBox
        aLat, aLon = browse.calculateCenter()
        aStrip.centerLat = aLat
        aStrip.centerLon = aLon

        #
        # try to cut in 3*3 blocks
        # the tile block are already at max 3 rows
        #
        if self.debug:
            print("\n#####\n#####\n#####\n WILL CREATE 3*3 blocks")
        n = 0
        allCellsMap = {}  # cell label x-y <-> list of tiles
        for aTileBlock in tileBlockList:
            if self.debug:
                print((" doing block[%s]: order=%s; id=%s" % (n, aTileBlock.order, aTileBlock.id)))
            blockCellMap = {}
            for x in range(1, aTileBlock.maxCols + 1):
                for y in range(1, aTileBlock.maxRows + 1):
                    if self.debug:
                        print(("  checking x:%s and y;%s" % (x, y)))
                    blockTileLabel = '%s-%s' % (x, y)
                    if blockTileLabel in aTileBlock.tiles:
                        if self.debug:
                            print("   has a tile")
                        cellLabel = "%s__%s__%s-%s" % (aTileBlock.order, n, int(x / 4), int(y / 4))
                        if cellLabel in list(allCellsMap.keys()):
                            allCellsMap[cellLabel].append(aTileBlock.tiles[blockTileLabel])
                        else:
                            aList = []
                            aList.append(aTileBlock.tiles[blockTileLabel])
                            allCellsMap[cellLabel] = aList

                        if cellLabel in list(blockCellMap.keys()):
                            blockCellMap[cellLabel].append(aTileBlock.tiles[blockTileLabel])
                        else:
                            aList = []
                            aList.append(aTileBlock.tiles[blockTileLabel])
                            blockCellMap[cellLabel] = aList
                    else:
                        if self.debug:
                            print("   has NO tile")

            aTileBlock.cellsMap = blockCellMap

            n += 1

        if self.debug:
            print(("\n#####\n#####\n#####\n FINAL cells:%s" % list(allCellsMap.keys())))
        n = 0
        for item in list(allCellsMap.keys()):
            # firstJson = True
            fd = open("%s/%s__%s.json" % (self.jsonFileHome, cellDetailVectorObjectJson, item), 'w')
            self.initJson(fd)
            for aTile in allCellsMap[item]:
                self.extentToJson(fd, aTile.getWest(), aTile.getNorth(), aTile.getEast(), aTile.getSouth(),
                                  aTile.filename,
                                  "Col:%s" % aTile.col, "Row:%s" % aTile.row, "CELL Label:%s" % item)
            fd.flush()
            self.closeJson(fd)
            n += 1

        aStrip.cellsMap = allCellsMap

        # os._exit(1)

    def initJson(self, fd):
        self.firstJson = True
        fd.write('{ "type": "FeatureCollection",\n')
        fd.write('    "features":\n')
        fd.write('    [\n')
        fd.flush()

    def closeJson(self, fd):
        fd.write('\n    ]\n')
        fd.write('}')
        fd.flush()
        fd.close()
        self.firstJson = False

    #
    #
    def extentToJson(self, fd, nwLong, nwLat, seLong, seLat, order, country, city, luzId='LuzId'):
        # global firstJson
        #
        # CONTENT WILL BE LIKE:
        #
        # { "type": "FeatureCollection",
        #    "features":
        #    [
        #        {"type":"Feature", "properties":{"order":"ORDER"}, "geometry":{"type":"Polygon", "coordinates":[PAIR_LONG_VIRGOLA_LAT_VIRGOLA]}},
        #    ]
        # }
        #
        #
        tmp = JSON_PATTERN.replace('PAIR_LONG_VIRGOLA_LAT_VIRGOLA', '[%s,%s],[%s,%s],[%s,%s],[%s,%s],[%s,%s]' % (
        nwLong, nwLat, seLong, nwLat, seLong, seLat, nwLong, seLat, nwLong, nwLat))
        tmp = tmp.replace('ORDER', order)
        country2 = country.replace('country:', '').strip()
        city2 = city.replace('city:', '').strip()
        tmp = tmp.replace('COUNTRY', country2)
        tmp = tmp.replace('CITY', city2)
        tmp = tmp.replace('LUZID', luzId)
        if self.debug:
            print("\nJSON=%s\n" % tmp)
        if self.firstJson:
            fd.write(tmp)
            self.firstJson = False
        else:
            fd.write(',\n' + tmp)
        fd.flush()

    #
    # entry point
    # - look for '^.*_Urban_Atlas_.*$', '^.xml$' files. Like: GSC#CR#ESA#VHR1-2_Urban_Atlas_2012#20151002#054228.xml
    # - parse them
    #
    # return a strip object
    #
    def process(self, aPath, re1, re2):
        if self.debug:
            print((" looking for worldview2 medatadata file at path:%s" % aPath))
        fileHelper = FileHelper()
        re1Prog = re.compile(re1)
        re2Prog = re.compile(re2)
        #
        start = time.time()
        aList = fileHelper.list_files(aPath, re1Prog, re2Prog)
        if self.debug:
            print((" >> found %s xml files" % len(aList)))

        aStrip = None
        anHelper = XmlHelper()
        for aFile in aList:
            if self.debug:
                print(("  doing file:%s" % aFile))
            fd = open(aFile, 'r')
            data = fd.read()
            fd.close()

            basePath = os.path.dirname(aFile)

            # get identifier: is also the name of the EO product folder
            anHelper.setData(data)
            anHelper.parseData()
            aNode = anHelper.getFirstNodeByPath(None,
                                                'opt_metadata/metaDataProperty/EarthObservationMetaData/identifier',
                                                None)
            id = anHelper.getNodeText(aNode).split(':')[-1]
            if self.debug:
                print((" > got identifier: %s" % id))

            txtPath = "%s/%s_01/%s_01_README.TXT." % (basePath, id, id)
            fd = open(txtPath, 'r')
            dataTxt = fd.read()
            fd.close()

            # xmlPath = "%s/%s_01/%s_01_README.XML." % (basePath, id, id)
            # fd=open(txtPath, 'r')
            # dataXml=fd.read()
            # fd.close()

            aStrip = Strip()
            aStrip.id = id
            self.parseReadmeData(basePath, aStrip, dataTxt)

        return aStrip

    #
    # converter entry point
    #
    def processAnWorldviewXml(self, apath, processInfo):
        basePath = os.path.dirname(apath)

        fd = open(apath, 'r')
        data = fd.read()
        fd.close()

        # get identifier: is also the name of the EO product folder
        anHelper = XmlHelper()
        anHelper.setData(data)
        anHelper.parseData()
        aNode = anHelper.getFirstNodeByPath(None, 'opt_metadata/metaDataProperty/EarthObservationMetaData/identifier',
                                            None)
        id = anHelper.getNodeText(aNode).split(':')[-1]
        if self.debug:
            print((" > got identifier: %s" % id))

        txtPath = "%s/%s_01/%s_01_README.TXT" % (basePath, id, id)
        fd = open(txtPath, 'r')
        dataTxt = fd.read()
        fd.close()

        aStrip = Strip()
        aStrip.id = id
        self.parseReadmeData(basePath, aStrip, dataTxt, processInfo)
        return aStrip


#
#
#
def main():
    try:
        aPath = '/home/gilles/shared/WEB_TOOLS/MISSIONS/Worldview2/NEW_DATASET'
        if len(sys.argv) > 1:
            aPath = sys.argv[1]

        print((" will process worldview products at path:%s" % aPath))

        grouper = TileGrouper()
        grouper.process(aPath, '^.*_Urban_Atlas_.*$', '^.xml$')


    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
