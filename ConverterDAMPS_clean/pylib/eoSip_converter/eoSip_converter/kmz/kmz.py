import os
import sys
import traceback
import zipfile
from optparse import OptionParser

from ..esaProducts.browseImage import BrowseImage
from ..esaProducts import metadata
from ..xmlHelper import XmlHelper

DEBUG = True
KML_TEMPLATE = 'TEMPLATE.KML'
ORBIT_DIRECTION_PATH = 'procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitDirection'
LINEAR_RING_PATH = 'featureOfInterest/Footprint/multiExtentOf/MultiSurface/surfaceMember/Polygon/exterior/LinearRing/posList'
SCENE_CENTER_PATH = 'featureOfInterest/Footprint/centerOf/Point/pos'
SPECIFIC_ATTRIBUTES_PATH = 'metaDataProperty/EarthObservationMetaData/vendorSpecific/SpecificInformation'
EXT_SIP_ZIP = '.SIP.ZIP'
EXT_ZIP = '.ZIP'


class Kmz:
    def __init__(self):
        self.debug = DEBUG
        self.ID = None
        self.description = None
        self.index = -1
        self.orbitDirection = None
        self.footprint = None
        self.sceneCenter = None
        self.bbox = None
        self.useBBox = None
        self.browseIsOrtho = None
        self.reportName = None
        self.xmlData = None
        self.browseName = None
        self.browseData = None
        self.center = None
        self.browse = None  # BrowseIm
        self.processInfo = None
        self.product = None  # EoSip product
        self.zipPath = None  # zip file path

    def processWithZip(self, destPath):
        self.getXmldataFromZip()
        self.getBrowseDatafromZip()
        self.getId()
        self.getCoordsInfoFromZip()
        self.buildKmlRing()

    def processWithConverter(self):
        self.getProductFromEoSip()
        self.getBrowseFromEoSip()
        self.getId()
        self.getCoordsInfoFromConverter()

    def buildKmlRing(self):
        result = ''
        if self.useBBox:
            if self.bbox is None:
                raise Exception("want to use BBOX, but BBOX is None")
            self.buildKmlRingFromBbox()
        else:
            self.buildKmlRingFromFootprint()

    def buildKmlRingFromFootprint(self):
        # if ascending: we have footprint CCW starting at LR: LR, UR, UL, LL, LR
        # if descending: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
        # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL

        resultLonLat = ''
        coords = self.footprint.split(' ')
        n = 0
        if self.orbitDirection == "DESCENDING":
            if self.debug:
                print("  ## descending case, we want to reverse footprint")
            for i in repr(list(range(len(coords) // 2))):
                lat = coords[(i * 2)]
                lon = coords[(i * 2) + 1]
                if len(resultLonLat) > 0:
                    resultLonLat += ' '
                resultLonLat += "%s,%s,0" % (lon, lat)
                if self.debug:
                    print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                n = n + 1

            # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # --> index 1,2,3,0,1
            result2 = ''
            toks = resultLonLat.split(' ')
            result2 = "%s" % (toks[1])
            result2 += " %s" % (toks[2])
            result2 += " %s" % (toks[3])
            result2 += " %s" % (toks[0])
            result2 += " %s" % (toks[1])

        else:
            if self.debug:
                print("  ## ascending case")
            for i in range(len(coords) // 2):
                lat = coords[(i * 2)]
                lon = coords[(i * 2) + 1]
                if len(resultLonLat) > 0:
                    resultLonLat += ' '
                resultLonLat += "%s,%s,0" % (lon, lat)
                if self.debug:
                    print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                n = n + 1

            if self.debug:
                print("  top left CW: lon,lat,elev ring:'%s'" % resultLonLat)

            # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # --> index 3,0,1,2,3
            result2 = ''
            toks = resultLonLat.split(' ')
            result2 = "%s" % (toks[3])
            result2 += " %s" % (toks[0])
            result2 += " %s" % (toks[1])
            result2 += " %s" % (toks[2])
            result2 += " %s" % (toks[3])

        # get a lat space lon representation for test purpose
        toks = result2.split(',0 ')
        latLon = ''
        for tok in toks:
            if len(latLon) > 0:
                latLon += " "
            latLon += "%s %s" % (tok.split(",")[1], tok.split(",")[0])
        print(("  makeLinearRing FINAL footprint like 'lat space lon space' string:%s" % latLon))

        print(("  makeLinearRing FINAL KML 'lon,lat space' string:%s" % result2.replace(',0 ', ' ')[0:-2]))

    def buildKmlRingFromBbox(self):
        # BBOX: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
        # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
        pass

    def getCoordsInfoFromZip(self):
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ ")
        # extact metadata
        helper = XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.xmlData)
        helper.parseData()

        # get orbit direction
        tmpNodes = []
        helper.getNodeByPath(None, ORBIT_DIRECTION_PATH, None, tmpNodes)
        if len(tmpNodes) == 0:
            raise Exception('can not get xml element at ORBIT_DIRECTION_PATH:%s' % ORBIT_DIRECTION_PATH)
        self.orbitDirection = helper.getNodeText(tmpNodes[0])
        if self.debug:
            print((" ## orbit direction:%s" % self.orbitDirection))

        # get footprint
        tmpNodes = []
        helper.getNodeByPath(None, LINEAR_RING_PATH, None, tmpNodes)
        if len(tmpNodes) == 0:
            raise Exception('can not get xml element at LINEAR_RING_PATH:%s' % LINEAR_RING_PATH)
        self.footprint = helper.getNodeText(tmpNodes[0])
        if self.debug:
            print((" ## footprint:%s" % self.footprint))

        # get scene center if any
        tmpNodes = []
        helper.getNodeByPath(None, SCENE_CENTER_PATH, None, tmpNodes)
        if len(tmpNodes) == 0:
            print(('can not get xml element at SCENE_CENTER_PATH:%s' % SCENE_CENTER_PATH))
            # get from footprint
            self.browse = BrowseImage()
            self.browse.setFootprint(self.footprint)
            self.browse.calculateCenter()
            self.browse.calculateBoondingBox()
            print((" #### browseIm info:%s" % self.browse.info()))
            self.sceneCenter = self.browse.getCenter()
        else:
            self.sceneCenter = helper.getNodeText(tmpNodes[0])
        if self.debug:
            print((" ## sceneCenter:%s" % (self.sceneCenter,)))

        # get bbox if any
        tmpNodes = []
        helper.getNodeByPath(None, SPECIFIC_ATTRIBUTES_PATH, None, tmpNodes)
        tmp = None
        for node in tmpNodes:
            aChildren = helper.getNodeChildrenByName(node, 'localAttribute')
            helper.setDebug(True)
            tmp = helper.getNodeText(aChildren[0])
            if self.debug:
                print(("  ##### localAttribute:%s'" % tmp))
            if tmp == 'boundingBox':
                aChildren = helper.getNodeChildrenByName(node, 'localValue')
                tmp = helper.getNodeText(aChildren[0])
                # add 5th closing node
                toks = tmp.split(' ')
                tmp = "%s %s %s" % (tmp, toks[0], toks[1])
                break
        if tmp is not None:
            self.bbox = tmp
            if self.debug:
                print((" ## bbox:%s" % self.bbox))

    #
    # retrieve metadata report from zip archive
    #
    def getXmldataFromZip(self):
        shortName = os.path.split(self.zipPath)[-1]
        if shortName.upper().endswith(EXT_SIP_ZIP):
            shortName = shortName[0:-len(EXT_SIP_ZIP)]
            if self.debug:
                print("  SIP shortname:%s" % shortName)

        elif shortName.upper().endswith(EXT_ZIP):
            shortName = shortName[0:-len(EXT_ZIP)]
            if self.debug:
                print("  SIP shortname:%s" % shortName)

        reportName = None
        reportData = None
        fh = open(self.zipPath, 'rb')
        z = zipfile.ZipFile(fh)
        n = 0
        d = 0
        for name in z.namelist():
            firstLevel = True
            if name.find(os.sep) >= 0:
                firstLevel = False

            if firstLevel:
                # print "  first level:"
                if name.upper().endswith('%s.XML' % shortName):
                    reportName = name
                    reportData = z.read(name)
                    if self.debug:
                        print("  found xml metadata report:%s" % reportName)
                    break

                elif name.upper().endswith('%s.MD.XML' % shortName):
                    reportName = name
                    reportData = z.read(name)
                    if self.debug:
                        print("  found xml metadata report:%s" % reportName)
                    break

            n = n + 1
            if name.endswith('/'):
                d = d + 1
                firstLevel = False

        z.close()
        fh.close()

        if reportData is None:
            raise Exception("MD xml metadata report data not found")

        self.reportName = reportName
        self.xmlData = reportData
        return reportData

    #
    # retrieve browse data and name from EoSip zip archive
    #
    def getBrowseDatafromZip(self):
        browseData = None
        browseName = None
        fh = open(self.zipPath, 'rb')
        z = zipfile.ZipFile(fh, 'r')
        n = 0
        d = 0
        for name in z.namelist():
            firstLevel = True
            if name.find('/') >= 0:
                firstLevel = False

            if firstLevel:
                if name.upper().endswith('.BID.PNG'):
                    browseName = name
                    browseData = z.read(browseName)
                elif name.upper().endswith('.PNG'):
                    browseName = name
                    browseData = z.read(browseName)
                elif name.upper().endswith('.JPG'):
                    browseName = name
                    browseData = z.read(browseName)
            n = n + 1

            if name.endswith('/'):
                d = d + 1
                firstLevel = False

            if browseName is not None:
                break

        z.close()
        fh.close()

        if browseName == None:
            raise Exception("no browse found in ZIP")
        self.browseName = browseName
        self.browseData = browseData
        print((" ## Kmz.getBrowseFromEoSip; readed browse data; length=%s" % len(self.browseData)))

    def getCoordsInfoFromConverter(self):
        self.orbitDirection = self.product.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        self.footprint = self.product.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        self.sceneCenter = self.product.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        if not self.product.metadata.valueExists(self.sceneCenter):
            # get from xml footprint
            self.browse = BrowseImage()
            self.browse.setFootprint(self.footprint)
            self.browse.calculateCenter()
            self.browse.calculateBoondingBox()
            print((" #### browseIm info:%s" % self.browse.info()))
            self.sceneCenter = self.browse.getCenter()

        if self.useBBox:
            self.bbox = self.product.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)

    def getProductFromEoSip(self):
        if self.index < 0:
            self.product = self.processInfo.destProduct
        else:
            self.product = self.processInfo.destProduct.getEoSip(self.index)

    def getId(self):
        # id
        browseNameInZip = self.browseName.split('/')[-1]
        self.id = browseNameInZip.split('.')[0]
        print((" ## Kmz.getBrowseFromEoSip; id:%s" % self.id))

    def getBrowseFromEoSip(self):
        print(" ## Kmz.getBrowseFromEoSip")
        self.browseName = self.product.sourceBrowsesPath[0]
        if len(self.product.sourceBrowsesPath) > 1:
            for aName in self.product.sourceBrowsesPath:
                if aName.find('.BID.') > 0:
                    browseName = aName
                    print(" use BID browse:%s" % browseName)
        fd = open(self.browseName, 'r')
        self.browseData = fd.read()
        fd.close()
        print((" ## Kmz.getBrowseFromEoSip; readed browse data; length=%s" % len(self.browseData)))


#
#
#
class KmzFactory:

    #
    #
    #
    def __init__(self):
        self.debug = DEBUG

    #
    # entry point from Zip EoSip file
    #
    def makeKmlFromZip(self, zipPath, destPath, useBBox, browseIsOrtho):
        print(" ## KmzFactory.makeKmlFromEoSip; zipPath=%s; destPath=%s; useBBox=%s; browseIsOrtho=%s")
        try:
            result = []
            aKmz = Kmz()
            aKmz.useBBox = useBBox
            .0
            aKmz.browseIsOrtho = browseIsOrtho
            aKmz.index = -1
            aKmz.zipPath = zipPath
            aKmz.processWithZip(destPath)
            return result

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error = "Problem creating kmz file(s) from zip: %s %s" % (exc_type, exc_obj)
            traceback.print_exc(sys.stdout)
            raise Exception(error)

    #
    # entry point from EoSip converter
    #
    def makeKmlFromEoSip(self, destPath, useBBox, browseIsOrtho, aProcessInfo):
        print(" ## KmzFactory.makeKmlFromEoSip; destPath=%s; useBBox=%s; browseIsOrtho=%s")
        try:
            eoSipPath = aProcessInfo.destProduct.getPath()
            result = None
            if isinstance(eoSipPath, list):
                result = []
                n = 0
                for iten in eoSipPath:
                    path = self.makeOneKmlFromEoSip(useBBox, destPath, browseIsOrtho, n, aProcessInfo)
                    result.append(path)
                    n = n + 1
            else:
                result = self.makeOneKmlFromEoSip(useBBox, destPath, browseIsOrtho, -1, aProcessInfo)
            return result

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error = "Problem creating kmz file(s) from converter: %s %s" % (exc_type, exc_obj)
            print(error)
            raise Exception(error)

    #
    # called from makeKmlFromEoSip converter
    #
    def makeOneKmlFromEoSip(self, useBBox, destPath, browseIsOrtho, index, aProcessInfo):
        print((" ## makeOneKmlFromEoSip; destPath=%s; useBBox=%s; browseIsOrtho=%s; index=%s" % (
        destPath, useBBox, browseIsOrtho, index)))

        aKmz = Kmz()
        aKmz.useBBox = useBBox
        aKmz.browseIsOrtho = browseIsOrtho
        aKmz.index = index
        aKmz.processInfo = aProcessInfo

        if index < 0:
            if self.debug:
                print(" ## KmzFactory.makeOneKml")
            product = aProcessInfo.destProduct
        else:
            if self.debug:
                print((" ## KmzFactory.makeOneKml (multiple case), index: %s" % index))
            product = aProcessInfo.destProduct.getEoSip(index)

        aKmz.processWithConverter()


#
PATH = '/home/gilles/shared/converter_workspace/outspace/image2006_new_glpkg/SPOT/SP4_OPER_HRI__X__2O_20050605T090007_N39-791_E026-958_0001.SIP.ZIP'


#
# use from command line
#
def main():
    """Main funcion"""

    print("sys.argv:%s" % sys.argv)

    path = PATH
    options = []
    parser = OptionParser()
    parser.add_option("-p", "--path", dest="path", help="eoSip path")
    parser.add_option("-b", "--boundingbox", dest="boundingBox", default=False,
                      help="use boundingBox instead of footprint")
    pOptions, args = parser.parse_args(sys.argv)

    if pOptions.path != None:
        path = pOptions.path
    else:
        # raise Exception('need a path, try -h for syntax')
        pass
    useBoundingBox = False
    if pOptions.boundingBox != None:
        print(" pOptions.boundingBox=%s" % pOptions.boundingBox)
        if pOptions.boundingBox == 'True':
            options.append('boundingbox')
            useBoundingBox = True

    # if true: the browse is already map oriented
    browseIsOrtho = False

    print((" will make a kmz from product at path:%s, useBoundingBox=%s; browseIsOrtho=%s" % (
    path, useBoundingBox, browseIsOrtho)))

    kmzfact = KmzFactory()
    kmzfact.makeKmlFromZip(path, './', useBoundingBox, browseIsOrtho)


if __name__ == "__main__":
    main()
