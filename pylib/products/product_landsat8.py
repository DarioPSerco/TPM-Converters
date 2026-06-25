# -*- coding: cp1252 -*-
#
# this class represent a quickbird product
#
#  - 
#  - 
#
#
import os
import shutil
import sys
import tarfile
import traceback
import zipfile
from os import listdir
from os.path import isfile, join
from subprocess import call

from . import browse_metadata
#
import eoSip_converter.esaProducts.verifier as verifier
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .groupedDocument import GroupedDocument
from .product_directory import Product_Directory
from xml_nodes import rep_footprint

# gdal commands to build browse from multi-band tif
GDAL_STEP_0 = 'gdal_translate -b 1 -outsize 25% 25% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 1 -outsize 25% 25% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 1 -outsize 25% 25% @SRC @DEST3'
# no resize
GDAL_STEP_N0 = 'gdal_translate -b 1 @SRC @DEST1'
GDAL_STEP_N1 = 'gdal_translate -b 1 @SRC @DEST2'
GDAL_STEP_N2 = 'gdal_translate -b 1 @SRC @DEST3'
#
GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
# GDAL_STEP_4='gdal_translate @DEST4 -scale 0 650 -ot Byte @DEST5'
# GDAL_STEP_4='gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'
#
GM_STEP_1 = 'gm convert @SRC -transparent black @DEST'

# gdal commands to build PNG browse from tif
# commandTifToPng="gdalwarp -t_srs EPSG:4326 -of PNG "
commandTifToPng = "gdal_translate -of PNG "
commandPngToTif = "gdal_translate -of GTiff "

#
#
#
# GDAL_STEP_0='gdal_translate -of png -outsize 25% 25% @SRC @DEST'

#
#
REF_TYPECODES = ['OAT_GTC_1P',
                 'OAT_GEO_1P',
                 'OAT_SP__2P',
                 'OAT_SR__2P']

#
#
REF_TIER_NAME = 'tier'
REF_TIER = ['T1', 'T2', 'RT']
REF_TIER_TO_ONE_DIGIT_MAPPING = {REF_TIER[0]: '1', REF_TIER[1]: '2', REF_TIER[2]: 'R'}
#
REF_SENSOR_NAME = 'sensor'
#
REF_COLLECTION_NAME = 'collection'
#
REF_STATIONS = ['M', 'K', 'L']

#
allXmlMapping = {}
#
# MAP_METADATA_PRODUCT_CONTENTS = {
#    'DATA_TYPE': 'DATA_TYPE',
# metadata.METADATA_SENSOR_NAME: 'SENSOR_ID',
# metadata.METADATA_CODESPACE_WRS_LATITUDE_DEG_NORMALISED: 'TARGET_WRS_ROW',
# metadata.METADATA_CODESPACE_WRS_LONGITUDE_DEG_NORMALISED: 'TARGET_WRS_PATH',
# metadata.METADATA_START_DATE: 'DATE_ACQUIRED', # like 2018-04-30
# 'SCENE_CENTER_TIME': 'SCENE_CENTER_TIME', # like "08:42:54.0148979Z"
# metadata.METADATA_START_TIME: 'SCENE_CENTER_TIME', # like "08:42:54.0148979Z"
#    metadata.METADATA_PROCESSING_TIME: 'FILE_DATE',
# }

#
MAP_METADATA_PROJECTION_ATTRIBUTES = {
    'CORNER_UL_LAT_PRODUCT': 'CORNER_UL_LAT_PRODUCT',
    'CORNER_UL_LON_PRODUCT': 'CORNER_UL_LON_PRODUCT',
    'CORNER_UR_LAT_PRODUCT': 'CORNER_UR_LAT_PRODUCT',
    'CORNER_UR_LON_PRODUCT': 'CORNER_UR_LON_PRODUCT',

    'CORNER_LL_LAT_PRODUCT': 'CORNER_LL_LAT_PRODUCT',
    'CORNER_LL_LON_PRODUCT': 'CORNER_LL_LON_PRODUCT',
    'CORNER_LR_LAT_PRODUCT': 'CORNER_LR_LAT_PRODUCT',
    'CORNER_LR_LON_PRODUCT': 'CORNER_LR_LON_PRODUCT',
}

#
MAP_METADATA_IMAGE_ATTRIBUTES = {
    metadata.METADATA_START_DATE: 'DATE_ACQUIRED',  # like 2018-04-30
    'SCENE_CENTER_TIME': 'SCENE_CENTER_TIME',  # like "08:42:54.0148979Z"
    metadata.METADATA_START_TIME: 'SCENE_CENTER_TIME',  # like "08:42:54.0148979Z"
    metadata.METADATA_CLOUD_COVERAGE: 'CLOUD_COVER',
    'CLOUD_COVER_LAND': 'CLOUD_COVER_LAND',
    metadata.METADATA_SUN_AZIMUTH: 'SUN_AZIMUTH',
    metadata.METADATA_SUN_ELEVATION: 'SUN_ELEVATION',
    metadata.METADATA_ACQUISITION_CENTER: 'STATION_ID',
}

allXmlMapping = {  # 'LANDSAT_METADATA_FILE/PRODUCT_CONTENTS': MAP_METADATA_PRODUCT_CONTENTS,
    'LANDSAT_METADATA_FILE/IMAGE_ATTRIBUTES': MAP_METADATA_IMAGE_ATTRIBUTES,
    'LANDSAT_METADATA_FILE/PROJECTION_ATTRIBUTES': MAP_METADATA_PROJECTION_ATTRIBUTES}

REF_PROCESSING_LEVEL = {'other: LV1B',
                        'other: LV2A'}

REF_ESA_STATION = ['KIS', 'MTI', 'KSS', 'LGN']

WITH_BOUNDINGBOX = ['OAT_GTC_1P']

METADATA_FILE_3DIGIT = "_MTL.txt"
QUALITY_FILE_3DIGIT = '_bqa.tif'  # before the .xxx extension
THERMAL_FILE_3DIGIT = '???'  # before the .xxx extension
TIFF_SUFFIX = ".tif"

# browses from .zip
THERMAL_SUFFIX = '_TIR.jpg'
QUALITY_SUFFIX = '_QB.jpg'


def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


class Product_Landsat8(Product_Directory):
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)

        # the companion .zip file. CONTAINS the .tif files to be used as browses.
        if not self.path.endswith('.tar'):
            raise Exception("product has bad extension, expected .tar:'%s'" % self.path)

        # the compagnion browse files
        self.compagnionFilePath = None
        self.compagnionFilePath_QB = None
        self.compagnionFilePath_TIR = None

        self.productLevel = 0  # will be 1 or 2
        # for L1: compagnion is a zip file
        # for L2: is the .jpg browse images
        toks = self.origName.split('_')
        if toks[1][1] == '1':
            self.productLevel = 1
            # if product is LC: it will have optical, thermal and quality images
            if toks[0][:2] == 'LC':
                self.compagnionFilePath = self.path.replace('.tar', '.jpg')
                if not os.path.exists(self.compagnionFilePath):
                    raise Exception("L1 product compagnion .jpg file does not exists:'%s'" % self.compagnionFilePath)

                self.compagnionFilePath_QB = self.path.replace('.tar', QUALITY_SUFFIX)
                if not os.path.exists(self.compagnionFilePath_QB):
                    raise Exception("L1 product compagnion %s file does not exists:'%s'" % (
                        QUALITY_SUFFIX, self.compagnionFilePath_QB))

                self.compagnionFilePath_TIR = self.path.replace('.tar', THERMAL_SUFFIX)
                if not os.path.exists(self.compagnionFilePath_TIR):
                    raise Exception("L1 product compagnion %s file does not exists:'%s'" % (
                        THERMAL_SUFFIX, self.compagnionFilePath_TIR))
            # if product is L0: it will have optical and quality images, no thermal
            elif toks[0][:2] == 'LO':
                self.compagnionFilePath = self.path.replace('.tar', '.jpg')
                if not os.path.exists(self.compagnionFilePath):
                    raise Exception("L1 product compagnion .jpg file does not exists:'%s'" % self.compagnionFilePath)

                self.compagnionFilePath_QB = self.path.replace('.tar', QUALITY_SUFFIX)
                if not os.path.exists(self.compagnionFilePath_QB):
                    raise Exception("L1 product compagnion %s file does not exists:'%s'" % (
                        QUALITY_SUFFIX, self.compagnionFilePath_QB))
            # if product is LT: it will have thermal and quality images, no optical
            elif toks[0][:2] == 'LT':
                self.compagnionFilePath_TIR = self.path.replace('.tar', THERMAL_SUFFIX)
                if not os.path.exists(self.compagnionFilePath_TIR):
                    raise Exception("L1 product compagnion %s file does not exists:'%s'" % (
                        THERMAL_SUFFIX, self.compagnionFilePath_TIR))

                self.compagnionFilePath_QB = self.path.replace('.tar', QUALITY_SUFFIX)
                if not os.path.exists(self.compagnionFilePath_QB):
                    raise Exception("L1 product compagnion %s file does not exists:'%s'" % (
                        QUALITY_SUFFIX, self.compagnionFilePath_QB))

        elif toks[1][1] == '2':
            self.productLevel = 2
            self.compagnionFilePath = self.path.replace('.tar', '.jpg')
            if not os.path.exists(self.compagnionFilePath):
                self.compagnionFilePath = self.findJpegInFolder(os.path.dirname(self.path))
                if self.compagnionFilePath is None:
                    raise Exception(
                        "L2 product compagnion .jpg file does not exists in folder:'%s'" % os.path.dirname(self.path))

        # the 2 needed file for generating additional quicklook
        # self.QUALITY_FILE=None # src file name
        self_QUALITY_QL = None  # quicklook path
        # self.THERMAL_FILE = None # src file name
        self_THERMAL_QL = None  # quicklook path

        self.metadataFile = None
        self.metadataPath = None
        self.metadataContent = None

        #
        self.TifMap = {}  # name, path

        #
        # self.useBbox=False

        #
        self.browseIm = None

        #
        self.browseDestPath = None
        self.opticalBrowseDestPath = None
        self.thermalBrowseDestPath = None
        self.qualityBrowseDestPath = None

        if self.debug != 0:
            print(" init class Product_Landsat8")

    #
    #
    #
    def findJpegInFolder(self, aPath):
        file_list = [f for f in listdir(aPath) if isfile(join(aPath, f))]
        for item in file_list:
            if item.lower().endswith('.jpg'):
                return join(aPath, item)
        return None

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
    def getTifForband(self, b):
        b = "%s" % b
        for item in self.TifMap:
            print((" #### test band '%s' VS file '%s'" % (b, item)))
            if item.lower().endswith("_b%s.tif" % b.lower()):
                return item, self.TifMap[item]

        raise Exception("tif file for band '%s' not found" % b)

    #
    # used by create browses
    #
    def makeOneSubBrowseCommand(self, resize, type, srcPath, destPath, processInfo):
        cellBrowseBase = "%s/%s_browse" % (processInfo.workFolder, type)
        if resize:
            command = GDAL_STEP_0.replace('@SRC', srcPath)
            command1 = command.replace('@DEST1', "%s_b1.tif" % cellBrowseBase)
        else:
            command = GDAL_STEP_N0.replace('@SRC', srcPath)
            command1 = command.replace('@DEST1', "%s_b1.tif" % cellBrowseBase)

        # use stretcherApp
        tmp_command = "%s -transparent %s %s/%s_transparent.png 0xff000000" % (
            self.stretcherApp, "%s_b1.tif" % cellBrowseBase, processInfo.workFolder, type)
        last_command = writeShellCommand(tmp_command, True)

        tmp_command = "%s -stretch %s/%s_transparent.png  %s/%s_stretched.png 0.01" % (
            self.stretcherApp, processInfo.workFolder, type, processInfo.workFolder, type)
        last_command = "%s\n\n%s" % (last_command, writeShellCommand(tmp_command, True))

        tmp_command = "%s -autoBrighten %s/%s_stretched.png %s 85" % (
            self.stretcherApp, processInfo.workFolder, type, destPath)
        last_command = "%s\n\n%s\n\necho\necho\necho %s browse done" % (
            last_command, writeShellCommand(tmp_command, True), type)

        return "%s\n\n\n\n%s" % (command1, last_command)

    #
    # use tifs in compagnion file to make browses
    #
    def makeBrowses(self, processInfo):
        """THERMAL_SUFFIX = '_TIR.tif'
        QUALITY_SUFFIX = '_QB.tif'
        self.compagnionZipPath
        self.browseDestPath = None
        self.thermalBrowseDestPath = None
        self.qualityBrowseDestPath = None
        # browseName = processInfo.destProduct.getEoProductName()
        """

        #
        browseToBeAdded = []

        if self.productLevel == 2:
            # L2: the file is the jpg browse
            browseName = processInfo.destProduct.getEoProductName()
            self.browseDestPath = "%s/%s.BI.JPG" % (processInfo.workFolder, browseName)
            shutil.copy(self.compagnionFilePath, self.browseDestPath)
            browseToBeAdded.append(self.browseDestPath)

        else:
            browseName = processInfo.destProduct.getEoProductName()
            # LC has optical, thermal and quality images
            if browseName[0:4] == 'LC08':
                self.browseDestPath = "%s/%s.BID.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath, self.browseDestPath)
                browseToBeAdded.append(self.browseDestPath)

                self.thermalBrowseDestPath = "%s/%s.BI_T.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath_TIR, self.thermalBrowseDestPath)
                browseToBeAdded.append(self.thermalBrowseDestPath)

                self.qualityBrowseDestPath = "%s/%s.BI_Q.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath_QB, self.qualityBrowseDestPath)
                browseToBeAdded.append(self.qualityBrowseDestPath)
            # LO has optical and quality images, no thermal
            elif browseName[0:4] == 'LO08':
                self.browseDestPath = "%s/%s.BID.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath, self.browseDestPath)
                browseToBeAdded.append(self.browseDestPath)

                self.qualityBrowseDestPath = "%s/%s.BI_Q.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath_QB, self.qualityBrowseDestPath)
                browseToBeAdded.append(self.qualityBrowseDestPath)
            # LT has thermal and quality, no optical
            elif browseName[0:4] == 'LT08':
                self.thermalBrowseDestPath = "%s/%s.BI_T.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath_TIR, self.thermalBrowseDestPath)
                browseToBeAdded.append(self.thermalBrowseDestPath)

                self.qualityBrowseDestPath = "%s/%s.BI_Q.JPG" % (processInfo.workFolder, browseName)
                shutil.copy(self.compagnionFilePath_QB, self.qualityBrowseDestPath)
                browseToBeAdded.append(self.qualityBrowseDestPath)

            if 1 == 2:  # disabled
                # L1: the file is a zip file
                print((
                        "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: use L1 compagnion file:%s" % self.compagnionFilePath))
                browseName = processInfo.destProduct.getEoProductName()

                fh = open(self.compagnionFilePath, 'rb')
                z = zipfile.ZipFile(fh)
                #
                n = 0
                for name in z.namelist():
                    n = n + 1
                    if 1 == 1 or self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  compagnion zip content[%d]:%s" % (n, name))
                    if name.endswith(THERMAL_SUFFIX):
                        self.thermalBrowseDestPath = "%s/%s.BI_T.tif" % (
                            processInfo.workFolder, processInfo.destProduct.getEoProductName())
                        outfile = open(self.thermalBrowseDestPath, 'wb')
                        outfile.write(z.read(name))
                        outfile.flush()
                        outfile.close()
                    elif name.endswith(QUALITY_SUFFIX):
                        self.qualityBrowseDestPath = "%s/%s.BI_Q.tif" % (
                            processInfo.workFolder, processInfo.destProduct.getEoProductName())
                        outfile = open(self.qualityBrowseDestPath, 'wb')
                        outfile.write(z.read(name))
                        outfile.flush()
                        outfile.close()
                    elif name.endswith(TIFF_SUFFIX):
                        self.opticalBrowseDestPath = "%s/%s.BI_O.tif" % (
                            processInfo.workFolder, processInfo.destProduct.getEoProductName())
                        outfile = open(self.opticalBrowseDestPath, 'wb')
                        outfile.write(z.read(name))
                        outfile.flush()
                        outfile.close()
                z.close()
                fh.close()

            print(" makeBrowses: found compagnion tifs:")
            # print("    self.browseDestPath:%s" % self.browseDestPath)
            print(("    self.opticalBrowseDestPath:%s" % self.opticalBrowseDestPath))
            print(("    self.qualityBrowseDestPath:%s" % self.qualityBrowseDestPath))
            print(("    self.thermalBrowseDestPath:%s" % self.thermalBrowseDestPath))

            set = None  # disabled
            if set == 1:  # set #1
                if browseName[0:4] == 'LC08':
                    self.browseDestPath = self.opticalBrowseDestPath.replace(".BI_O.tif", ".BID.PNG")
                    commands = "%s %s %s" % (commandTifToPng, self.opticalBrowseDestPath, self.browseDestPath)
                    commandFile = "%s/command_browse_LC08.sh" % processInfo.workFolder
                    launchCommand = "/bin/bash -i -f %s 2>&1 | tee %s/command_browse_LC08.stdout" % (
                        commandFile, processInfo.workFolder)
                    # write in command file
                    fd = open(commandFile, 'w')
                    fd.write(commands)
                    fd.flush()
                    fd.close()
                    #
                    retval = call(launchCommand, shell=True)
                    print(("  external make browse exit code:%s" % retval))
                    processInfo.addLog("  external make browse exit code:%s" % retval)
                    if retval != 0:
                        raise Exception("Error generating browse, exit coded:%s" % retval)

                    print(" makeBrowses: LC08 case:")
                    print(("    self.browseDestPath; copy of Optical (.BID.PNG):%s" % self.browseDestPath))
                    print(("    self.opticalBrowseDestPath           (.BI_O.tif):%s" % self.opticalBrowseDestPath))
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    print(("    self.thermalBrowseDestPath           (.BI_T.tif):%s" % self.thermalBrowseDestPath))
                    browseToBeAdded.append(self.browseDestPath)
                    browseToBeAdded.append(self.opticalBrowseDestPath)
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    browseToBeAdded.append(self.thermalBrowseDestPath)

                elif browseName[0:4] == 'LO08':
                    self.browseDestPath = self.opticalBrowseDestPath.replace(".BI_O.tif", ".BID.PNG")
                    commands = "%s %s %s" % (commandTifToPng, self.opticalBrowseDestPath, self.browseDestPath)
                    commandFile = "%s/command_browse_LC08.sh" % processInfo.workFolder
                    launchCommand = "/bin/bash -i -f %s 2>&1 | tee %s/command_browse_LC08.stdout" % (
                        commandFile, processInfo.workFolder)
                    # write in command file
                    fd = open(commandFile, 'w')
                    fd.write(commands)
                    fd.flush()
                    fd.close()
                    #
                    retval = call(launchCommand, shell=True)
                    print(("  external make browse exit code:%s" % retval))
                    processInfo.addLog("  external make browse exit code:%s" % retval)
                    if retval != 0:
                        raise Exception("Error generating browse, exit coded:%s" % retval)

                    print(" makeBrowses: LO08 case:")
                    print(("    self.browseDestPath; copy of Optical (.BID.PNG):%s" % self.browseDestPath))
                    print(("    self.opticalBrowseDestPath           (.BI_O.tif):%s" % self.opticalBrowseDestPath))
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    browseToBeAdded.append(self.browseDestPath)
                    browseToBeAdded.append(self.opticalBrowseDestPath)
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    # os._exit(1)

                elif browseName[0:4] == 'LT08':
                    self.browseDestPath = self.thermalBrowseDestPath.replace(".BI_T.tif", ".BID.PNG")
                    commands = "%s %s %s" % (commandTifToPng, self.thermalBrowseDestPath, self.browseDestPath)
                    commandFile = "%s/command_browse_LT08.sh" % processInfo.workFolder
                    launchCommand = "/bin/bash -i -f %s 2>&1 | tee %s/command_browse_LT08.stdout" % (
                        commandFile, processInfo.workFolder)
                    # write in command file
                    fd = open(commandFile, 'w')
                    fd.write(commands)
                    fd.flush()
                    fd.close()
                    #
                    retval = call(launchCommand, shell=True)
                    print(("  external make browse exit code:%s" % retval))
                    processInfo.addLog("  external make browse exit code:%s" % retval)
                    if retval != 0:
                        raise Exception("Error generating browse, exit coded:%s" % retval)

                    print(" makeBrowses: LT08 case:")
                    print(("    self.browseDestPath; copy of Optical (.BID.PNG):%s" % self.browseDestPath))
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    print(("    self.thermalBrowseDestPath           (.BI_T.tif):%s" % self.thermalBrowseDestPath))
                    browseToBeAdded.append(self.browseDestPath)
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    browseToBeAdded.append(self.thermalBrowseDestPath)
                else:
                    raise Exception("invalid product 4 first digits:'" % browseName[0:4] + "'")

            elif set == 2:  # set #2
                if browseName[0:4] == 'LC08':
                    print(" makeBrowses: LC08 case:")
                    bid_path = self.opticalBrowseDestPath.replace(".BI_O.tif", ".BID.tif")
                    shutil.copy(self.opticalBrowseDestPath, bid_path)
                    print(("    self.opticalBrowseDestPath           (.BID.tif):%s" % bid_path))
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    print(("    self.thermalBrowseDestPath           (.BI_T.tif):%s" % self.thermalBrowseDestPath))
                    browseToBeAdded.append(bid_path)
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    browseToBeAdded.append(self.thermalBrowseDestPath)

                elif browseName[0:4] == 'LO08':
                    bid_path = self.opticalBrowseDestPath.replace(".BI_O.tif", ".BID.tif")
                    shutil.copy(self.opticalBrowseDestPath, bid_path)
                    print(" makeBrowses: LO08 case:")
                    print(("    self.browseDestPath; copy of Optical (.BID.tif):%s" % bid_path))
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    browseToBeAdded.append(bid_path)
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    # os._exit(1)

                elif browseName[0:4] == 'LT08':
                    bid_path = self.thermalBrowseDestPath.replace(".BI_T.tif", ".BID.tif")
                    shutil.copy(self.thermalBrowseDestPath, bid_path)
                    print(" makeBrowses: LT08 case:")
                    print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                    print(("    self.thermalBrowseDestPath           (.BID.tif):%s" % bid_path))
                    browseToBeAdded.append(self.qualityBrowseDestPath)
                    browseToBeAdded.append(bid_path)
                else:
                    raise Exception("invalid product 4 first digits:'" % browseName[0:4] + "'")
                # os._exit(1)

        anEosip = processInfo.destProduct
        for aBrowsePath in browseToBeAdded:
            print(("  make browseChoice for browse at path:%s" % aBrowsePath))

            if aBrowsePath is not None:

                # set AM time if needed
                anEosip.setFileAMtime(aBrowsePath)
                processInfo.destProduct.addSourceBrowse(aBrowsePath, [])
                processInfo.addLog(" main browse image added: name=%s; path=%s" % (browseName, aBrowsePath))

                # create browse choice for browse metadata report
                bmet = anEosip.browse_metadata_dict[aBrowsePath]
                if self.debug != 0:
                    print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

                reportBuilder = rep_footprint.rep_footprint()
                #
                if self.debug != 0:
                    print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
                browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                               "rep:browseReport/rep:browse/rep:footprint").strip()
                if self.debug != 0:
                    print("browseChoiceBlock:%s" % browseChoiceBlock)
                bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

                # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
                # if specified in configuration
                tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
                if tmp != None:
                    bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

                # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
                tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
                if tmp != None:
                    bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

                processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print((" Will extract directory product '%s' to path:%s" % (self.path, folder)))

        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print((" Will extract product to path:%s" % folder))

        #
        self.num_preview = 0
        # EO_FOLDER
        self.EO_FOLDER = "%s/EO_FOLDER" % folder
        #
        tar = tarfile.open(self.path, 'r')
        #
        n = 0
        for tarinfo in tar:
            name = tarinfo.name
            if self.debug != 0:
                print((" ## product content[%d]:'%s'" % (n, name)))
            dest = "%s/%s" % (self.EO_FOLDER, name)

            if 1 == 2 and name.lower().endswith(TIFF_SUFFIX):  # disabled
                if self.debug != 0:
                    print((" #### found a tif:'%s'" % name))
                self.TifMap[name] = dest
                if dont_extract != True:
                    fd = tar.extractfile(tarinfo)
                    data = fd.read()
                    fd.close()

                    parent = os.path.dirname(dest)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)

                    outfile = open(dest, 'wb')
                    outfile.write(data)
                    outfile.flush()
                    outfile.close()

                if name.lower().endswith(QUALITY_FILE_3DIGIT):
                    self.QUALITY_FILE = name
                elif name.lower().endswith(THERMAL_FILE_3DIGIT):
                    self.THERMAL_FILE = name

            elif name.endswith(METADATA_FILE_3DIGIT):
                if self.debug != 0:
                    print((" #### found metadata file:'%s'" % name))
                fd = tar.extractfile(tarinfo)
                self.metadataFile = name
                self.metadataPath = dest
                self.metadataContent = fd.read()
                fd.close()

                parent = os.path.dirname(dest)
                # print "   parent:%s" % (parent)
                if not os.path.exists(parent):
                    os.makedirs(parent)

                outfile = open(self.metadataPath, 'wb')
                outfile.write(self.metadataContent)
                outfile.flush()
                outfile.close()

            if self.debug:
                print(("   content[%s] EO_FOLDER item path:%s" % (n, name)))
            # self.contentList.append(name)

            n += 1
        tar.close()

        # print(" #### extract done; TifMap:%s" % self.TifMap)
        print((" extract done; metadata file:%s" % self.metadataFile))
        # print(" #### quality file:%s" % self.QUALITY_FILE)
        # print(" #### thermal file:%s" % self.THERMAL_FILE)
        # os._exit(1)

    #
    #
    #
    def getMetadataFromFilename(self, met, processInfo=None):
        # like:
        # LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CC_TX_FT.ext
        #
        # LC08_L1GT_181011_20180430_20180430_01_T2_KIS.tar.gz
        # LO08_L1TP_198027_20181115_20181115_01_T2_MTI.tar.gz
        # LT08_L1GT_200029_20130507_20170504_01_T2.tar.gz

        """
        L
        Landsat
        X
        Sensor of: O = OLI, T = TIRS, C = Combined TIRS and OLI Indicates which sensor collected data for this product
        SS
        Landsat satellite (08 for Landsat 8)
        LLLL
        Processing level (L1TP, L1GT, L1GS)
        PPP
        Satellite orbit location in reference to the Worldwide Reference System-2 (WRS-2) path of the product
        RRR
        Satellite orbit location in reference to the WRS-2 row of the product
        YYYY
        Acquisition year of the image
        MM
        Acquisition month of the image
        DD
        Acquisition day of the image
        yyyy
        Processing year of the image
        mm
        Processing month of the image
        dd
        Processing day of the image
        CC
        Collection number (e.g. 01)
        TX
        Tier of the image: "RT" for Real-time, "T1" for Tier 1 (highest quality), "T2" for Tier 2
        _FT
        File type, where FT equals one of the following: image band file number (B1�B11), MTL (metadata file), BQA (Quality Band file), MD5 (checksum file), ANG (angle coefficient file)
        .ext
        File extension, where .TIF equals GeoTIFF file extension, and .txt equals text extension
        """

        toks = self.origName.split('_')
        sensor = None
        satId = None
        level = None
        if toks[0][1] == 'T':
            sensor = 'TIRS'
        elif toks[0][1] == 'O':
            sensor = 'OLI'
        elif toks[0][1] == 'C':
            sensor = 'COMBINED'
        else:
            raise Exception("Unknown sensor in filename tokens:'%s'" % toks[0])
        met.setMetadataPair(REF_SENSOR_NAME, sensor)

        satId = toks[0][-2:]
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, satId[-1])

        level = toks[1]
        met.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, level)

        kj = toks[2]  # path row
        # met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, '0%s' % kj[0:2])
        # met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, '0%s' % kj[3:5])

        # lon: 1 to 233
        if int(kj[0:3]) < 0 or int(kj[0:3]) > 233:
            raise Exception("invalid lon/track value:'%s'" % kj[0:3])
        # lat: 1 to 248
        if int(kj[3:6]) < 0 or int(kj[0:3]) > 248:
            raise Exception("invalid lat/frame value:'%s'" % kj[3:6])
        # met.setMetadataPair(metadata.METADATA_TRACK, '0%s' % kj[0:3])
        # met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, '0%s' % kj[0:3])
        # met.setMetadataPair(metadata.METADATA_FRAME, '0%s' % kj[3:6])
        # met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, '0%s' % kj[3:6])

        track = int(kj[0:3])
        if track < 1 or track > 233:
            raise Exception("invalid track %s, not in range 1->233" % track)
        met.setMetadataPair(metadata.METADATA_TRACK, '%s' % track)
        met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, '%s' % track)

        row = int(kj[3:6])
        if row < 1 or row > 248:
            raise Exception("invalid row %s, not in range 1->248" % row)
        met.setMetadataPair(metadata.METADATA_FRAME, '%s' % row)
        met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, '%s' % row)

        collection = toks[5]
        met.setMetadataPair(REF_COLLECTION_NAME, collection)

        tier = toks[6].split('.')[0]
        if tier not in REF_TIER:
            raise Exception("Unknown tier in filename tokens:'%s'" % tier)
        met.setMetadataPair(REF_TIER_NAME, tier)

        # metadata value if any
        metadataStation = met.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        if not met.valueExists(metadataStation):
            metadataStation = None
        # file name value if any
        filenameStation = None
        if len(toks) >= 8:
            filenameStation = toks[7].split('.')[0]

        if filenameStation is None and metadataStation is None:
            raise Exception("no station info found")
        elif filenameStation is not None and metadataStation is not None:
            if filenameStation != metadataStation:
                raise Exception("station info mismatch: '%s' VS '%s'" % (metadataStation, filenameStation))

        stationOk = metadataStation
        if stationOk is None:
            stationOk = filenameStation

        if len(stationOk) != 3:
            raise Exception("invalid station length in filename, should be 3:'%s'" % stationOk)
        else:
            if stationOk[0] not in REF_STATIONS:
                raise Exception("First digit of station not in the valid list(%s): '%s' from '%s'" % (
                    REF_STATIONS, stationOk[0], stationOk))

            if stationOk not in REF_ESA_STATION:
                print(("### metadata station not in REF_ESA_STATION: %s VS %s" % (stationOk, REF_ESA_STATION)))
                # met.deleteMetadata(metadata.METADATA_ACQUISITION_CENTER)
                raise Exception("station not in ref list: '%s' VS '%s'" % (stationOk, REF_ESA_STATION))

                # if processInfo is not None:
                #    processInfo.addLog("##### remove non ESA acq station:'%s'" % stationOk)
            else:
                if processInfo is not None:
                    processInfo.addLog("##### keep ESA acq station:'%s'" % stationOk)

        #
        print((" getMetadataFromFilename returns:%s" % stationOk))
        if processInfo is not None:
            processInfo.addLog(" ## getMetadataFromFilename returns stationOk:%s" % stationOk)
        # os._exit(1)
        return stationOk

    #
    #
    #
    def extractOneMetadataGroup(self, met, groupDoc, group):
        if self.debug:
            print((" @@@@ extractOneMetadataGroup for group:%s" % group))
        groupMapping = allXmlMapping[group]
        start, stop = groupDoc.getGroupByPath(group)
        if self.debug:
            print((" PRODUCT_PARAMETERS for group '%s': start line:%s; stop line:%s" % (group, start, stop)))
        n = 0
        for item in list(groupMapping.keys()):
            keyName = groupMapping[item]
            if self.debug:
                print((" - extracting metadata key: %s" % item))
            aValue = 'NOT-FOUND'
            for i in range(start, stop):
                aLine = groupDoc.getLine(i)
                # print("  @@ look for info[%s]='%s' key='%s' at line index:%s. Line:%s" % (n, item, keyName, i, aLine))
                if aLine.find(keyName) >= 0:
                    aValue = aLine.split('=')[1].strip().replace('"', '')
                    if self.debug:
                        print((" -> %s %s found" % (item, keyName)))
                    break
            if self.debug:
                print((" --> info[%s]=%s: %s" % (n, item, aValue)))
            if aValue != 'NOT-FOUND':
                met.setMetadataPair(item, aValue)
            n += 1

    #
    #
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met == None:
            raise Exception("metadate is None")

        if self.metadataPath is None:
            raise Exception("no metadata file found")

        #
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        groupDoc = GroupedDocument()
        groupDoc.loadDocument(self.metadataPath)

        for agroup in allXmlMapping:
            self.extractOneMetadataGroup(met, groupDoc, agroup)
        # os._exit(1)

        """
        start, stop = groupDoc.getGroupByPath('L1_METADATA_FILE/PRODUCT_METADATA')
        print " @@##@@ PRODUCT_PARAMETERS group: start line:%s; stop line:%s" % (start, stop)

        n=0
        for item in MAP_METADATA.keys():
            keyName=MAP_METADATA[item]
            print(" - extracting metadata key: %s" % item)
            aValue = 'NOT-FOUND'
            for i in range(start, stop):
                aLine = groupDoc.getLine(i)
                #print("  @@ look for info[%s]='%s' key='%s' at line index:%s. Line:%s" % (n, item, keyName, i, aLine))
                if aLine.find(keyName) >= 0:
                    aValue = aLine.split('=')[1].strip().replace('"', '')
                    print " -> %s %s found" % (item, keyName)
                    break
            print " --> info[%s]=%s: %s" % (n, item, aValue)
            if aValue != 'NOT-FOUND':
                met.setMetadataPair(item, aValue)
            n+=1

        os._exit(1)

        
        # extact metadata
        helper=xmlHelper.XmlHelper()
        #helper.setDebug(1)
        helper.setData(self.metadata_content)
        helper.parseData()
        num_added = 0
        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print "  -->%s=%s" % (field, aValue)
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        print("metadata extracted: %s" % num_added)"""

        #
        usedAcq = self.getMetadataFromFilename(met, processInfo)

        # define file class
        """
        # The field <CCCC> of the filename will become:
         - First character fixed to O (for Operational)
         - 1 character for the category (R, 1, 2) -----> Real Time, T1, T2
         - 1 character for the sensor (O = OLI, T = TIRS, C = Combined TIRS and OLI)
         - 1 character for the station (one character for the station (M, K, L)
           i.e., ====> O (R-1-2)(O-T-C)(M-K-L) 
        """
        # sensor value check already done
        sensor = met.getMetadataValue(REF_SENSOR_NAME)
        if sensor is None:
            raise Exception("sensor is None")
        #
        # acq = met.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        # if acq[0] not in REF_STATIONS:
        #    raise Exception("Unknown acquisition station first digit:'%s' from '%s'. ref:%s" % (acq[0], acq, REF_STATIONS))
        # tier value check already done
        tier = met.getMetadataValue(REF_TIER_NAME)
        if tier is None:
            raise Exception("tier is None")
        #
        fileClass = "O%s%s%s" % (REF_TIER_TO_ONE_DIGIT_MAPPING[tier], sensor[0], usedAcq[0])
        print(("fileClass:%s" % fileClass))
        met.setMetadataPair(metadata.METADATA_FILECLASS, fileClass)
        # os._exit(1)

        self.metadata = met

        #
        self.refineMetadata(processInfo)

        #
        self.extractFootprint(processInfo)

        #
        self.buildTypeCode(processInfo)

        # os._exit(1)

    #
    # extract the footprint
    #
    def extractFootprint(self, processInfo):

        footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                    (
                        self.metadata.getMetadataValue("CORNER_UL_LAT_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_UL_LON_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_LL_LAT_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_LL_LON_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_LR_LAT_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_LR_LON_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_UR_LAT_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_UR_LON_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_UL_LAT_PRODUCT"),
                        self.metadata.getMetadataValue("CORNER_UL_LON_PRODUCT")
                    )

        """footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                      (
                        self.metadata.getMetadataValue("ULLat"), self.metadata.getMetadataValue("ULLon"),
                        self.metadata.getMetadataValue("LLLat"), self.metadata.getMetadataValue("LLLon"),
                        self.metadata.getMetadataValue("LRLat"), self.metadata.getMetadataValue("LRLon"),
                        self.metadata.getMetadataValue("URLat"), self.metadata.getMetadataValue("URLon"),
                        self.metadata.getMetadataValue("ULLat"), self.metadata.getMetadataValue("ULLon")
                       )"""

        #
        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        try:
            verifier.verifyFootprint(footprint, True)  # all descending
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS NOT REVERESED")
            if self.debug:
                print((" #### footprint non reversed:%s" % footprint))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("verifyFootprint step 0 '%s' error: %s; %s" % (footprint, exc_type, exc_obj)))
            traceback.print_exc(file=sys.stdout)
            reversed = browseIm.reverseFootprint()
            if self.debug:
                print(("verifyFootprint step 1 '%s'" % reversed))
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
            if self.debug:
                print((" #### footprint ok from reversed:%s" % reversed))

        clat, clon = browseIm.calculateCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
        flon = float(clon)
        flat = float(clat)
        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
        if flat < 0:
            flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        """
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)
        """

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo):

        # start and stop
        sd = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        st = self.metadata.getMetadataValue(metadata.METADATA_START_TIME).replace('"', '')
        if st.find('.') > 0:
            tmp = "%s.%s" % (st.split('.')[0], st.split('.')[1][0:3])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%s" % (sd, tmp))
        else:
            tmp = "%s.000" % st
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%s" % (sd, tmp))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, sd)

        # test metadata.METADATA_CLOUD_COVERAGE
        cc = -1
        try:
            scc = self.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE)
            cc = int(float(scc))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("cloud coverage check error on '%s': %s; %s" % (scc, exc_type, exc_obj)))
            traceback.print_exc(file=sys.stdout)
            # sys._exit(1)
        if cc > 100 or cc < -1:
            raise Exception("invalid final cloud coverage: %s" % cc)
        self.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, "%s" % cc)

    #
    #
    #
    def buildTypeCode(self, processInfo):
        level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        levelDigit = '1'
        if level == 'L1GT':
            sensorMode = 'GEO'
        elif level == 'L1TP':
            sensorMode = 'GTC'
        elif level == 'L2SP':
            sensorMode = 'SP_'
            levelDigit = '2'
        elif level == 'L2SR':
            sensorMode = 'SR_'
            levelDigit = '2'
        else:
            raise Exception("Unknown processing level:%s" % level)
        typecode = "OAT_%s_%sP" % (sensorMode, levelDigit)

        if not typecode in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown typecode:'%s'" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        #
        self.metadata.addLocalAttribute("originalName", self.origName.split('.')[0])

        #
        tier = self.metadata.getMetadataValue(REF_TIER_NAME)
        self.metadata.addLocalAttribute("collectionCategory", tier)

        #
        # if typecode in WITH_BOUNDINGBOX:
        #    self.useBbox = True
        # processInfo.addLog("## has boundingBox:%s" % typecode)
        self.metadata.addLocalAttribute("boundingBox", self.browseIm.getBoundingBox())
        # else:

    #     processInfo.addLog("## has NO boundingBox:%s" % typecode)

    #
    # extract quality
    #
    def extractQuality(self, helper):
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
