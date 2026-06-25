# -*- coding: cp1252 -*-
#
# this class represent a proba product, which is composed of several files
#
#
import os

#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from .product import Product

# for verification
REF_TYPECODE = {'CHR_MO1_1P', 'CHR_MO2_1P', 'CHR_MO3_1P', 'CHR_MO4_1P', 'CHR_MO5_1P', 'HRC_HRC_1P'}


class Product_Proba(Product):
    xmlMapping = {
        metadata.METADATA_START_DATE: 'update/updateMetadata/modify/metadata/dataExt/tempEle/exTemp/beginEnd/begin',
        metadata.METADATA_STOP_DATE: 'update/updateMetadata/modify/metadata/dataExt/tempEle/exTemp/beginEnd/end',

        # like: PROBA
        metadata.METADATA_PLATFORM: 'update/updateMetadata/modify/metadata/dataIdInfo/plaInsId/platfSNm',
        # like: CHRIS
        metadata.METADATA_INSTRUMENT: 'update/updateMetadata/modify/metadata/dataIdInfo/plaInsId/instShNm',
        # like: C1
        metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'update/updateMetadata/modify/metadata/dataIdInfo/plaInsId/instMode',

        metadata.METADATA_FOOTPRINT: 'update/updateMetadata/modify/metadata/dataExt/geoEle/polygon/coordinates',
        metadata.METADATA_SCENE_CENTER: 'update/updateMetadata/modify/metadata/dataExt/geoEle/scCenter/coordinates',

        # like: CHRIS_YY_180410_4735_41
        metadata.METADATA_IDENTIFIER: 'update/updateMetadata/modify/metadata/dataIdInfo/idCitation/citID/identCode',

        metadata.METADATA_SUN_ELEVATION: 'update/updateMetadata/modify/metadata/contInfo/illElevAng',

        metadata.METADATA_ACQUISITION_CENTER: 'update/updateMetadata/modify/metadata/mdcontact/rpOrgName',

        'SITE_NAME': 'update/updateMetadata/modify/metadata/dataExt/exDesc'
        }

    #
    # CHRIS and HRC product are made of several file
    # both have a xml file, so this will be the source reference
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        self.isCHRIS = False
        self.isHRC = False

        if not self.origName.lower().endswith('.xml'):
            raise Exception("wrong input for converter:'%s' should be an .xml file" % self.origName.lower())

        self.metadataSrcPath = self.path
        if not os.path.exists(self.metadataSrcPath):
            raise Exception('xml metadata file not found:%s' % self.metadataSrcPath)
        fd = open(self.metadataSrcPath, 'r')
        self.metadataSrcContent = fd.read()
        fd.close()

        if self.origName.find('CHRIS_') >= 0:
            self.isCHRIS = True
            print(" product is CHRIS")
        elif self.origName.find('_HRC_') >= 0:
            print(" product is HRC")
            self.isHRC = True
        else:
            raise Exception("cannot recognize input file:%s. Doesn't contain 'CHRIS_' or '_HRC_'" % self.origName)

        self.zipSrcPath = None
        self.imageSrcPath = None
        self.bmpSrcPath = None

        if self.debug != 0:
            print(" init class Product_Proba")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # read matadata file
    #
    def getMetadataInfo(self):
        pass

    #
    #
    #
    def makeBrowses(self, processInfo):
        pass

    #
    # handle the input product files:
    # it is made of several files:
    #  - a zip + a xml + a jpg for CHRIS
    #  - a xml + a jpg + a bmp for HRC
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

        pos = self.path.rfind('.')
        if pos <= 0:
            raise Exception('product has incorrect name: extension problem:%s' % self.path)
        ext = self.path[pos:]

        # xml
        self.contentList.append(self.path)
        # src size: all pieces size
        self.tmpSize = os.stat(self.path).st_size

        # jpg
        self.imageSrcPath = self.path[0:pos] + '.jpg'
        if not os.path.exists(self.imageSrcPath):
            raise Exception('no jpg found:%s' % self.imageSrcPath)
        self.contentList.append(self.imageSrcPath)
        self.tmpSize += os.stat(self.imageSrcPath).st_size

        # bmp for HRC
        if self.isHRC:
            self.bmpSrcPath = self.path[0:pos] + '.bmp'
            if not os.path.exists(self.bmpSrcPath):
                raise Exception('no bmp found:%s' % self.bmpSrcPath)
            self.contentList.append(self.bmpSrcPath)
            self.tmpSize += os.stat(self.bmpSrcPath).st_size

        # zip for CHRIS
        if self.isCHRIS:
            self.zipSrcPath = self.path[0:pos] + '.zip'
            if not os.path.exists(self.zipSrcPath):
                raise Exception('no zip found:%s' % self.zipSrcPath)
            self.contentList.append(self.zipSrcPath)
            self.tmpSize += os.stat(self.zipSrcPath).st_size

    #
    #
    #
    def buildTypeCode(self):
        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        opmode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if tmp == 'CHRIS':
            if self.isHRC:
                raise Exception("buildTypeCode conflict: instrument don't match CHRIS filename:%s" % tmp)

            ## opmode can be C1-5; C10 C20 C30 C40 C50
            opmodeOk = None
            if not opmode.startswith('C'):
                raise Exception("invalide METADATA_SENSOR_OPERATIONAL_MODE; bad start; not C:'%s'" % opmode)
            if len(opmode) == 2:
                if int(opmode[-1]) < 1 or int(opmode[-1]) > 5:
                    raise Exception("invalide METADATA_SENSOR_OPERATIONAL_MODE; bad 2 digit value:'%s'" % opmode)
                opmodeOk = opmode[-1]
            elif len(opmode) == 3:
                if opmode[-1] != '0':
                    raise Exception("invalide METADATA_SENSOR_OPERATIONAL_MODE; bad end, not 0:'%s'" % opmode)
                if int(opmode[-2]) < 1 or int(opmode[-2]) > 5:
                    raise Exception("invalide METADATA_SENSOR_OPERATIONAL_MODE; bad 3 digit value:'%s'" % opmode)
                opmodeOk = opmode[-2]
            else:
                raise Exception("invalide METADATA_SENSOR_OPERATIONAL_MODE; bad length:'%s'" % opmode)

            typecode = "CHR_MO%s_1P" % opmodeOk
            self.isCHRIS = True
        else:
            if self.isCHRIS:
                raise Exception("buildTypeCode conflict: instrument don't match HRC filename:%s" % tmp)
            typecode = "HRC_HRC_1P"
            self.isHRC = True

        if not typecode in REF_TYPECODE:
            raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met is None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataSrcContent is None:
            raise Exception("no metadata to be parsed")

        # set size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.tmpSize)

        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metadataSrcContent)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData is None:
                aValue = None
            else:
                if attr is None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

                    # if self.DEBUG!=0:
            print("  num_added[%s] -->%s=%s" % (num_added, field, aValue))

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # local attributes
        # remove extension from original name
        pos = self.origName.find('.')
        if pos > 0:
            self.origName = self.origName[0:pos]
        met.addLocalAttribute("originalName", self.origName)

        # targetCode for CHRIS only: second token of filename like: CHRIS_KA_161024_2DF4_41
        if self.isCHRIS:
            met.addLocalAttribute("targetCode", self.origName.split('_')[1])
        # siteName
        met.addLocalAttribute("siteName", met.getMetadataValue('SITE_NAME'))

        self.metadata = met

        return num_added

    #
    # refine the metada
    #
    def refineMetadata(self):
        #
        self.buildTypeCode()

        # set the start stop date and time
        # is like: 2018-04-10T07:02:00Z
        # OR: 2016-12-10T51:00 AMZ
        # OR: 2017-01-26T26:00 PMZ
        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, tmp.split('T')[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp.split('T')[1].replace('Z', ''))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, tmp.split('T')[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp.split('T')[1].replace('Z', ''))

        # remove eventual .xx in start stop time
        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)
        if tmp.find('.') > 0:
            print("remove .xxx from METADATA_STOP_TIME")
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp[0:tmp.find('.')])
        else:
            print("no .xxx in METADATA_STOP_TIME:%s" % tmp)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        if tmp.find('.') > 0:
            print("remove .xxx from METADATA_START_TIME")
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp[0:tmp.find('.')])
        else:
            print("no .xxx in METADATA_START_TIME:%s" % tmp)

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set WRS grid
        # is like: +22.73,+114.83
        center = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        clat = float(center.split(',')[0])
        clon = float(center.split(',')[1])
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, clon)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))

        flon = float(clon)
        flat = float(clat)
        # avoid representation error, by parsing as a string as some point, then cut decimal
        mseclon = formatUtils.formatFloatDecimalNoRepresentationError(flon, 3)
        mseclat = formatUtils.formatFloatDecimalNoRepresentationError(flat, 3)
        print(" mseclon=%s; mseclat=%s" % (mseclon, mseclat))

        """
        mseclon=abs(int((flon-int(flon))*1000))
        mseclat=abs(int((flat-int(flat))*1000))
        """
        # os._exit(1)

        if flat < 0:
            flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)

        # adjust footprint. is like: +37.14,-06.44 +37.12,-06.28 +37.00,-06.30 +37.02,-06.46
        # may be error on latitude: > 90, implement a test
        #
        # for ascending bbbox is clockwise from top-left, not closed
        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        footprint = ''
        toks = tmp.split(' ')
        first = None
        for pair in toks:
            if first == None:
                first = pair
            if len(footprint) > 0:
                footprint += ' '
            # test
            if float(pair.split(',')[0]) > 90 or float(pair.split(',')[0]) < -90:
                raise Exception("latitude error:%s" % pair.split(',')[0])
            if float(pair.split(',')[1]) > 180 or float(pair.split(',')[1]) < -180:
                raise Exception("longitude error:%s" % pair.split(',')[1])

            footprint += "%s %s" % (float(pair.split(',')[0]), float(pair.split(',')[1]))
        footprint += " %s %s" % (float(first.split(',')[0]), float(first.split(',')[1]))
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        #
        if self.isCHRIS:
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
                                          'urn:esa:eop:PROBA:CHRIS:operationalMode')
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED,
                                          'urn:esa:eop:PROBA:TileColumn')
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED,
                                          'urn:esa:eop:PROBA:TileRow')
            # adjust mode
            tmp = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, "MODE-%s" % tmp[-1])

        if self.isHRC:
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
                                          'urn:esa:eop:PROBA:HRC:operationalMode')
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED,
                                          'urn:esa:eop:PROBA:TileColumn')
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED,
                                          'urn:esa:eop:PROBA:TileRow')
            # mode fixed: DEFAULT
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'DEFAULT')

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
        pass

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)
