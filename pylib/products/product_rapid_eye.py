# -*- coding: cp1252 -*-
#
# this class represent a rapideye product, which is composed of several files
#
#
import os
import shutil
import subprocess
from subprocess import call

#
import eoSip_converter.xmlHelper as xmlHelper
# import browse_metadata
from . import formatUtils
from . import metadata
# from product_directory import Product_Directory
# from xml_nodes import sipBuilder
from .browseImage import BrowseImage
from .product import Product

# import eoSip_converter.imageUtil as imageUtil
# import eoSip_converter.geomHelper as geomHelper


# for verification
REF_TYPECODE = {'MSI_IMG_1B', 'MSI_IMG_3A'}

# gdal commands
GDAL_STEP_0 = 'gdal_translate -b 1 -ot byte -scale 0 65535 0 255 -outsize 33% 33% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 2 -ot byte -scale 0 65535 0 255 -outsize 33% 33% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 3 -ot byte -scale 0 65535 0 255 -outsize 33% 33% @SRC @DEST3'

# GDAL_STEP_0='gdal_translate -b 1 -ot byte -scale 0 65535 0 255 @SRC @DEST1'
# GDAL_STEP_1='gdal_translate -b 2 -ot byte -scale 0 65535 0 255 @SRC @DEST2'
# GDAL_STEP_2='gdal_translate -b 3 -ot byte -scale 0 65535 0 255 @SRC @DEST3'
GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
# GDAL_STEP_4='gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'
GDAL_STEP_4 = 'gdal_translate @DEST4 -ot Byte @DEST5'
#
TIF_SUFFIX = '_Analytic.tif'


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


class Product_RapidEye(Product):
    xmlMapping = {metadata.METADATA_START_DATE: 'validTime/TimePeriod/beginPosition',
                  metadata.METADATA_STOP_DATE: 'validTime/TimePeriod/endPosition',

                  # like: RE-5
                  'platFormSerialIdentifier': 'using/EarthObservationEquipment/platform/Platform/serialIdentifier',
                  # like:
                  metadata.METADATA_INSTRUMENT: 'using/EarthObservationEquipment/instrument/Instrument/shortName',
                  # like: PUSHBROOM
                  # metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'using/EarthObservationEquipment/sensor/Sensor/scanType',
                  #
                  metadata.METADATA_RESOLUTION: 'using/EarthObservationEquipment/sensor/Sensor/resolution',

                  metadata.METADATA_ORBIT_DIRECTION: 'using/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitDirection',
                  metadata.METADATA_SUN_AZIMUTH: 'using/EarthObservationEquipment/acquisitionParameters/Acquisition/illuminationAzimuthAngle',
                  metadata.METADATA_SUN_ELEVATION: 'using/EarthObservationEquipment/acquisitionParameters/Acquisition/illuminationElevationAngle',

                  metadata.METADATA_FOOTPRINT: 'target/Footprint/multiExtentOf/MultiSurface/surfaceMembers/Polygon/exterior/LinearRing/posList',
                  metadata.METADATA_SCENE_CENTER: 'target/Footprint/centerOf/Point/pos',

                  # like:
                  metadata.METADATA_IDENTIFIER: 'metaDataProperty/EarthObservationMetaData/identifier',

                  metadata.METADATA_CLOUD_COVERAGE: 'resultOf/EarthObservationResult/cloudCoverPercentage',

                  metadata.METADATA_PROCESSING_TIME: 'metaDataProperty/EarthObservationMetaData/archivedIn/ArchivingInformation/archivingDate',

                  metadata.METADATA_ACQUISITION_CENTER: 'metaDataProperty/EarthObservationMetaData/downlinkedTo/DownlinkInformation/acquisitionStation',
                  'tileId': 'metaDataProperty/EarthObservationMetaData/tileId',
                  # 'site': '',
                  }

    xmlMappingNewFormat = {
        metadata.METADATA_FOOTPRINT: 'target/Footprint/multiExtentOf/MultiSurface/surfaceMembers/Polygon/outerBoundaryIs/LinearRing/coordinates',
    }

    #
    # rapid-eye product are made of several file
    # both have a xml file, so this will be the source reference
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        # NEW FORMAT
        self.newFormatFlag = False
        self.tifPath = None
        self.stretcherAppExe = None

        if not self.origName.lower().endswith('.xml'):
            raise Exception("wrong input for converter:'%s' should be an .xml file" % self.origName.lower())

        self.imageSrcPath = None

        self.metadataSrcPath = self.path
        if not os.path.exists(self.metadataSrcPath):
            raise Exception('xml metadata file not found:%s' % self.metadataSrcPath)
        fd = open(self.metadataSrcPath, 'r')
        self.metadataSrcContent = fd.read()
        fd.close()

        if self.debug != 0:
            print(" init class Product_RapidEye")

    #
    #
    #
    def runBrowseCommands(self, processInfo):
        print(" runBrowseCommands")
        processInfo.addLog("    runBrowseCommands")
        #
        print("prepareBrowseCommands: src=%s; dest=%s" % (self.tifPath, self.browseDestPath))

        # extract 3 band, equialize
        destPathBase = self.browseDestPath.replace('.PNG', '_')
        command = GDAL_STEP_0.replace('@SRC', "%s" % self.tifPath)
        command1 = command.replace('@DEST1', "%s_R.tif" % destPathBase)

        command2 = GDAL_STEP_1.replace('@SRC', "%s" % self.tifPath)
        command2 = command2.replace('@DEST2', "%s_G.tif" % destPathBase)

        command3 = GDAL_STEP_2.replace('@SRC', "%s" % self.tifPath)
        command3 = command3.replace('@DEST3', "%s_B.tif" % destPathBase)

        command4 = GDAL_STEP_3.replace('@DEST1', "%s_R.tif" % destPathBase).replace('@DEST2', "%s_G.tif" % (
            destPathBase)).replace('@DEST3', "%s_B.tif" % destPathBase)
        command4 = command4.replace('@DEST4', "%s_bmerged.tif" % destPathBase)

        command5 = "%s -transparent %s %s 0xff000000" % (
            self.stretcherAppExe, "%s_bmerged.tif" % destPathBase, "%s_transparent.tif" % destPathBase)

        command6 = "%s -stretch %s %s 0.01" % (
            self.stretcherAppExe, "%s_transparent.tif" % destPathBase, "%s_transparent_stretched.tif" % destPathBase)

        command7 = "%s -autoBrighten %s %s 85" % (
            self.stretcherAppExe, "%s_transparent_stretched.tif" % destPathBase, self.browseDestPath)

        commands = "%s%s%s%s%s%s%s" % (
            writeShellCommand(command1, True), writeShellCommand(command2, True), writeShellCommand(command3, True),
            writeShellCommand(command4, True), writeShellCommand(command5, True), writeShellCommand(command6, True),
            writeShellCommand(command7, True))

        commands = "%s\necho\necho\necho 'browse 2 done'" % commands

        #
        commandFile = "%s/command_browse.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        # command="/bin/sh -f %s" % (commandFile)
        # launch the main make_browse script:
        command = "/bin/bash -i -f %s/command_browse.sh >%s/command_browse.stdout 2>&1" % (
            processInfo.workFolder, processInfo.workFolder)
        #
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            print("Error generating browse, exit coded:%s" % retval)
            aStdout = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            print("Error generating browse, stdout:" % aStdout)
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

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
        if self.debug != 0:
            print(" makeBrowses")
        processInfo.addLog(" makeBrowses")
        # anEosip = processInfo.destProduct
        # browseName = processInfo.destProduct.getSipProductName()
        # self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)

        # use external command
        self.runBrowseCommands(processInfo)

    #
    # handle the input product files:
    # it is made of several files:
    # there is a xxxx_metadata.xml
    # there is a xxxx_browse.tif file
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

        # xml metadata
        # self.contentList.append(self.path)
        # src size
        # self.tmpSize = os.stat(self.path).st_size
        shutil.copy(self.path, "%s/%s" % (folder, self.origName))

        # get content
        srcParent = os.path.split(self.path)[0]
        n = 0
        size = 0
        for root, dirs, files in os.walk(srcParent, topdown=False):
            for name in files:
                aPath = os.path.join(srcParent, root, name)
                print((" check source file[%s]:%s" % (n, aPath)))
                size += os.stat(aPath).st_size
                self.contentList.append(aPath)

                #
                if name.endswith('_metadata.xml'):
                    self.imageSrcPath = self.path.replace('_metadata.xml', '_browse.tif')
                    print("################# self.imageSrcPath:%s" % self.imageSrcPath)
                elif name.endswith(TIF_SUFFIX):
                    self.tifPath = os.path.join(srcParent, root, name)
                    print("################# self.tifPath:%s" % self.tifPath)
                n += 1

        if self.imageSrcPath is None:
            raise Exception("no browse found in src product")

        if not os.path.exists(self.imageSrcPath):
            # raise Exception("browse image not found, new product format?")
            print(" ## !!!!! browse image not found, new product format?")

        self.tmpSize = size

        print(" source product has %s files, size=%s" % (n, size))
        # os._exit(1)

    #
    #
    #
    def buildTypeCode(self):
        typecode = 'MSI_IMG_3A'
        if not typecode in REF_TYPECODE:
            raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

    #
    #
    #
    def extractmetadataNewFormat(self):
        # extact metadata
        helper = xmlHelper.XmlHelper()
        helper.setDebug(1)
        helper.setData(self.metadataSrcContent)
        helper.parseData()
        num_added = 0
        for field in self.xmlMappingNewFormat:
            if self.xmlMappingNewFormat[field].find("@") >= 0:
                attr = self.xmlMappingNewFormat[field].split('@')[1]
                path = self.xmlMappingNewFormat[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMappingNewFormat[field]

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

            self.metadata.setMetadataPair(field, aValue)
            num_added = num_added + 1

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
        # met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, -1)

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
        met.addLocalAttribute("originalName", self.origName.replace('_metadata', ''))

        # size of src files
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.tmpSize)

        self.metadata = met
        return num_added

    #
    # refine the metada
    #
    def refineMetadata(self, processInfo):

        # test new/old format:
        clat = None
        clon = None
        tmp = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        if tmp is None:
            self.newFormatFlag = True
            # is like lon lat:
            tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
            # swap it
            clat = formatUtils.EEEtoNumber(tmp.split(' ')[1])
            clon = formatUtils.EEEtoNumber(tmp.split(' ')[0])
        else:
            # is like lat lon: 3.631237e+01 -7.073768e+01
            tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
            clat = formatUtils.EEEtoNumber(tmp.split(' ')[0])
            clon = formatUtils.EEEtoNumber(tmp.split(' ')[1])

        # adjust scene center. is like: 3.631237e+01 -7.073768e+01
        # tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        # clat = formatUtils.EEEtoNumber(tmp.split(' ')[0])
        # clon = formatUtils.EEEtoNumber(tmp.split(' ')[1])
        # print "################# scene center clat:'%s'  clon:'%s'" % (clat, clon)
        # self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (a, b))

        # also illumination angles
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_AZIMUTH)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, formatUtils.EEEtoNumber(tmp))
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_ELEVATION)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_ELEVATION, formatUtils.EEEtoNumber(tmp))

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

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set WRS grid
        # is like: +22.73,+114.83
        # center = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        # clat = float(center.split(' ')[0])
        # clon = float(center.split(' ')[1])
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

        # adjust footprint:
        # -  from EEE number to normal
        # - reverse it
        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        footprint = ''
        # new format
        if tmp is None:
            self.extractmetadataNewFormat()
            # are lon,lat space
            # put it right
            fp = ''
            tmp = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
            for tok in tmp.split(' '):
                if len(fp) > 0:
                    fp += ' '
                fp += tok.split(',')[1]
                fp += ' ' + tok.split(',')[0]
            print(("FOOTPRINT:%s" % fp))
            processInfo.addLog(" ###### new format original footprint:%s" % fp)
            tmp = fp
        else:
            processInfo.addLog(" ###### old format original footprint:%s" % tmp)

        toks = tmp.split(' ')
        for coord in toks:
            if len(footprint) > 0:
                footprint += ' '
            footprint += formatUtils.EEEtoNumber(coord)
        processInfo.addLog(" ###### footprint EEEtoNumber:%s" % footprint)

        browseImage = BrowseImage()
        if not self.newFormatFlag:
            processInfo.addLog(" ###### reverse footprint")
            tmp = browseImage.reverseSomeFootprint(footprint)
        else:
            processInfo.addLog(" ###### DONT reverse footprint")
            tmp = footprint
        print(("FOOTPRINT 1:%s" % tmp))
        # os._exit(1)

        browseImage.setFootprint(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, tmp)
        processInfo.addLog(" ###### final footprint:%s" % tmp)

        # add boundingBox
        browseImage.calculateBoondingBox()
        self.metadata.addLocalAttribute("boundingBox", browseImage.getBoundingBox())

        # add tileId
        self.metadata.addLocalAttribute("tileId", self.metadata.getMetadataValue('tileId'))

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
