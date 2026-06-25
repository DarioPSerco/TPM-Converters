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
                 'OAT_GEO_1P']

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
MAP_METADATA_PRODUCT_METADATA = {
    'DATA_TYPE': 'DATA_TYPE',
    # metadata.METADATA_SENSOR_NAME: 'SENSOR_ID',
    # metadata.METADATA_CODESPACE_WRS_LATITUDE_DEG_NORMALISED: 'TARGET_WRS_ROW',
    # metadata.METADATA_CODESPACE_WRS_LONGITUDE_DEG_NORMALISED: 'TARGET_WRS_PATH',
    metadata.METADATA_START_DATE: 'DATE_ACQUIRED',  # like 2018-04-30
    metadata.METADATA_START_TIME: 'SCENE_CENTER_TIME',  # like "08:42:54.0148979Z"
    metadata.METADATA_PROCESSING_TIME: 'FILE_DATE',

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
    metadata.METADATA_CLOUD_COVERAGE: 'CLOUD_COVER',
    'CLOUD_COVER_LAND': 'CLOUD_COVER_LAND',
    metadata.METADATA_SUN_AZIMUTH: 'SUN_AZIMUTH',
    metadata.METADATA_SUN_ELEVATION: 'SUN_ELEVATION',
}
#
MAP_METADATA_FILE_INFO = {
    metadata.METADATA_ACQUISITION_CENTER: 'STATION_ID',
}

allXmlMapping = {'L1_METADATA_FILE/PRODUCT_METADATA': MAP_METADATA_PRODUCT_METADATA,
                 'L1_METADATA_FILE/IMAGE_ATTRIBUTES': MAP_METADATA_IMAGE_ATTRIBUTES,
                 'L1_METADATA_FILE/METADATA_FILE_INFO': MAP_METADATA_FILE_INFO}

# RESOLUTION_LIMIT = 0.1

REF_PROCESSING_LEVEL = {'other: LV1B',
                        'other: LV2A'}

REF_ESA_STATION = ['MTI', 'KSS', 'LGN']

WITH_BOUNDINGBOX = ['OAT_GTC_1P']

METADATA_FILE_3DIGIT = "_MTL.txt"
QUALITY_FILE_3DIGIT = '_bqa.tif'  # before the .xxx extension
THERMAL_FILE_3DIGIT = '???'  # before the .xxx extension
TIFF_SUFFIX = ".tif"

# browses from .zip
THERMAL_SUFFIX = '_TIR.tif'
QUALITY_SUFFIX = '_QB.tif'


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


#
#
#
class Product_Landsat8(Product_Directory):

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)

        # will store source file inside EO ZIP
        # self.contentList.append(self.path)

        # the companion .zip file. CONTAINS the .tif files to be used as browses.
        if not self.path.endswith('.tar'):
            raise Exception("product has bad extension, expected .tar:'%s'" % self.path)

        # self.compagnionZipPath = self.path.replace('.tar', '.zip')
        # if not os.path.exists(self.compagnionZipPath):
        #     raise Exception("product compagnion zip file does not exists:'%s'" % self.compagnionZipPath)

        # the 2 needed file for generating additional quicklook
        self.QUALITY_FILE = None  # src file name
        self_QUALITY_QL = None  # quicklook path
        self.THERMAL_FILE = None  # src file name
        self_THERMAL_QL = None  # quicklook path

        self.metadataFile = None
        self.metadataPath = None
        self.metadataContent = None

        #
        self.TifMap = {}  # name, path

        #
        self.useBbox = False

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
    # create browses
    #
    def makeBrowses_orig(self, processInfo):

        anEosip = processInfo.destProduct

        #
        browseToBeDone = []

        # main browse
        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath = "%s/%s.BID.PNG" % (processInfo.workFolder, browseName)
        # thermal browse
        self.thermalBrowseDestPath = "%s/%s.BI_T.PNG" % (processInfo.workFolder, browseName)
        # quality browse
        self.qualityBrowseDestPath = "%s/%s.BI_Q.PNG" % (processInfo.workFolder, browseName)

        # aDict={} # name, path
        # aDict[browseName]=''
        browseToBeDone.append(self.browseDestPath)
        browseToBeDone.append(self.thermalBrowseDestPath)
        browseToBeDone.append(self.qualityBrowseDestPath)

        resize = True

        #
        # MAIN browse
        # band used for normal browse: 4 3 2
        #
        b1Name, b1Path = self.getTifForband(4)
        b2Name, b2Path = self.getTifForband(3)
        b3Name, b3Path = self.getTifForband(2)

        cellBrowseBase = "%s/browse" % processInfo.workFolder
        if resize:
            command = GDAL_STEP_0.replace('@SRC', b1Path)
            command1 = command.replace('@DEST1', "%s_b1.tif" % cellBrowseBase)
            command2 = GDAL_STEP_1.replace('@SRC', b2Path)
            command2 = command2.replace('@DEST2', "%s_b2.tif" % cellBrowseBase)
            command3 = GDAL_STEP_2.replace('@SRC', b3Path)
            command3 = command3.replace('@DEST3', "%s_b3.tif" % cellBrowseBase)
        else:
            command = GDAL_STEP_N0.replace('@SRC', b1Path)
            command1 = command.replace('@DEST1', "%s_b1.tif" % cellBrowseBase)
            command2 = GDAL_STEP_N1.replace('@SRC', b2Path)
            command2 = command2.replace('@DEST2', "%s_b2.tif" % cellBrowseBase)
            command3 = GDAL_STEP_N2.replace('@SRC', b3Path)
            command3 = command3.replace('@DEST3', "%s_b3.tif" % cellBrowseBase)

        # @DEST1 @DEST2 @DEST3 -o @DEST4
        command4 = GDAL_STEP_3.replace('@DEST1', "%s_b1.tif" % cellBrowseBase).replace('@DEST2', "%s_b2.tif" % (
            cellBrowseBase)).replace('@DEST3', "%s_b3.tif" % cellBrowseBase)
        command4 = command4.replace('@DEST4', "%s_bmerged.tif" % cellBrowseBase)
        # command5 = GDAL_STEP_4.replace('@DEST4', "%s_bmerged.tif" % (cellBrowseBase)).replace('@DEST5', "%s_bmerged.tif" % (cellBrowseBase))
        commands = "%s%s%s%s" % (
            writeShellCommand(command1, True), writeShellCommand(command2, True), writeShellCommand(command3, True),
            writeShellCommand(command4, True))  # , writeShellCommand(command5, True))

        # PNG not transparent
        # tmp_command = "%s  %s/block_%s.TIF %s/block_%s.PNG" % (self.tifToPngExe, processInfo.workFolder, key, processInfo.workFolder, key)
        # use stretcherApp
        tmp_command = "%s -transparent %s %s/transparent.png 0xff000000" % (
        self.stretcherApp, "%s_bmerged.tif" % cellBrowseBase, processInfo.workFolder)
        last_command = writeShellCommand(tmp_command, True)

        tmp_command = "%s -stretch %s/transparent.png  %s/stretched.png 0.01" % (
        self.stretcherApp, processInfo.workFolder, processInfo.workFolder)
        last_command = "%s\n\n%s" % (last_command, writeShellCommand(tmp_command, True))

        tmp_command = "%s -autoBrighten %s/stretched.png %s 85" % (
        self.stretcherApp, processInfo.workFolder, self.browseDestPath)
        last_command = "%s\n\n%s\n\necho\necho\necho MAIN browse done" % (
        last_command, writeShellCommand(tmp_command, True))

        # thermal browse command
        b1Name, b1Path = self.getTifForband(10)
        tbCommand = self.makeOneSubBrowseCommand(resize, 'T', b1Path, self.thermalBrowseDestPath, processInfo)
        print(("\n\n\n\n\n\n tbCommand:%s\n" % tbCommand))
        # os._exit(1)

        # quality browse command
        q1Name, q1Path = self.getTifForband('QA')
        qbCommand = self.makeOneSubBrowseCommand(resize, 'Q', q1Path, self.qualityBrowseDestPath, processInfo)
        print(("\n\n\n\n\n\n qbCommand:%s\n" % tbCommand))
        # os._exit(1)

        # write in command file
        commandFile = "%s/command_browse.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write("%s\n\n%s\n\n\n\n%s\n\n\n\n%s" % (commands, last_command, tbCommand, qbCommand))
        fd.close()

        # os._exit(1)

        # launch the main make_browse script:
        command = "/bin/bash -i -f %s 2>&1 | tee %s/command_browse.stdout" % (commandFile, processInfo.workFolder)
        # retval = call(command, shell=True)
        # print "  external make browse exit code:%s" % retval
        # processInfo.addLog("  external make browse exit code:%s" % retval)
        # if retval != 0:
        #    raise Exception("Error generating browse, exit coded:%s" % retval)

        for aBrowsePath in browseToBeDone:

            print("  make browseChoice for browse at path:%s" % aBrowsePath)

            # set AM time if needed
            anEosip.setFileAMtime(self.browseDestPath)
            processInfo.destProduct.addSourceBrowse(aBrowsePath, [])
            processInfo.addLog(" main browse image added: name=%s; path=%s" % (browseName, aBrowsePath))

            # set AM time if needed
            # anEosip.setFileAMtime(self.qualityBrowseDestPath)
            # processInfo.destProduct.addSourceBrowse(self.qualityBrowseDestPath, [])
            # processInfo.addLog(" main browse image added: name=%s; path=%s" % (os.path.basename(self.qualityBrowseDestPath), self.qualityBrowseDestPath))

            # set AM time if needed
            # anEosip.setFileAMtime(self.thermalBrowseDestPath)
            # processInfo.destProduct.addSourceBrowse(self.thermalBrowseDestPath, [])
            # processInfo.addLog(" main browse image added: name=%s; path=%s" % (os.path.basename(self.thermalBrowseDestPath), self.thermalBrowseDestPath))

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[aBrowsePath]
            if self.debug != 0:
                print("###\n###\n### BUILD L2 BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            #
            if self.debug != 0:
                print("###\n###\n### BUILD L2 BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != 0:
                print("browseChoiceBlock L2:%s" % browseChoiceBlock)
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

            processInfo.addLog(" L2 browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

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

        print(("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: use compagnion file:%s" % self.compagnionZipPath))
        browseName = processInfo.destProduct.getEoProductName()

        #
        # this is TDS CASE_1
        #
        #
        fh = open(self.compagnionZipPath, 'rb')
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
                outfile.close()
            elif name.endswith(QUALITY_SUFFIX):
                self.qualityBrowseDestPath = "%s/%s.BI_Q.tif" % (
                processInfo.workFolder, processInfo.destProduct.getEoProductName())
                outfile = open(self.qualityBrowseDestPath, 'wb')
                outfile.write(z.read(name))
                outfile.close()
            elif name.endswith(TIFF_SUFFIX):
                self.opticalBrowseDestPath = "%s/%s.BI_O.tif" % (
                processInfo.workFolder, processInfo.destProduct.getEoProductName())
                outfile = open(self.opticalBrowseDestPath, 'wb')
                outfile.write(z.read(name))
                outfile.close()
        z.close()
        fh.close()

        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: found compagnion tifs:")
        # print("    self.browseDestPath:%s" % self.browseDestPath)
        print(("    self.opticalBrowseDestPath:%s" % self.opticalBrowseDestPath))
        print(("    self.qualityBrowseDestPath:%s" % self.qualityBrowseDestPath))
        print(("    self.thermalBrowseDestPath:%s" % self.thermalBrowseDestPath))

        #
        browseToBeAdded = []

        set = 2
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
                print("  external make browse exit code:%s" % retval)
                processInfo.addLog("  external make browse exit code:%s" % retval)
                if retval != 0:
                    raise Exception("Error generating browse, exit coded:%s" % retval)

                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LC08 case:")
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
                print("  external make browse exit code:%s" % retval)
                processInfo.addLog("  external make browse exit code:%s" % retval)
                if retval != 0:
                    raise Exception("Error generating browse, exit coded:%s" % retval)

                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LO08 case:")
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
                print("  external make browse exit code:%s" % retval)
                processInfo.addLog("  external make browse exit code:%s" % retval)
                if retval != 0:
                    raise Exception("Error generating browse, exit coded:%s" % retval)

                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LT08 case:")
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
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LC08 case:")
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
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LO08 case:")
                print(("    self.browseDestPath; copy of Optical (.BID.tif):%s" % bid_path))
                print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                browseToBeAdded.append(bid_path)
                browseToBeAdded.append(self.qualityBrowseDestPath)
                # os._exit(1)

            elif browseName[0:4] == 'LT08':
                bid_path = self.thermalBrowseDestPath.replace(".BI_T.tif", ".BID.tif")
                shutil.copy(self.thermalBrowseDestPath, bid_path)
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ makeBrowses: LT08 case:")
                print(("    self.qualityBrowseDestPath           (.BI_Q.tif):%s" % self.qualityBrowseDestPath))
                print(("    self.thermalBrowseDestPath           (.BID.tif):%s" % bid_path))
                browseToBeAdded.append(self.qualityBrowseDestPath)
                browseToBeAdded.append(bid_path)
            else:
                raise Exception("invalid product 4 first digits:'" % browseName[0:4] + "'")
            # os._exit(1)

        anEosip = processInfo.destProduct
        for aBrowsePath in browseToBeAdded:

            if aBrowsePath is not None:
                print("  make browseChoice for browse at path:%s" % aBrowsePath)

                # set AM time if needed
                anEosip.setFileAMtime(aBrowsePath)
                processInfo.destProduct.addSourceBrowse(aBrowsePath, [])
                processInfo.addLog(" main browse image added: name=%s; path=%s" % (browseName, aBrowsePath))

                # create browse choice for browse metadata report
                bmet = anEosip.browse_metadata_dict[aBrowsePath]
                if self.debug != 0:
                    print("###\n###\n### BUILD L2 BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

                reportBuilder = rep_footprint.rep_footprint()
                #
                if self.debug != 0:
                    print("###\n###\n### BUILD L2 BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
                browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                               "rep:browseReport/rep:browse/rep:footprint").strip()
                if self.debug != 0:
                    print("browseChoiceBlock L2:%s" % browseChoiceBlock)
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

                processInfo.addLog(" L2 browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract directory product '%s' to path:%s" % (self.path, folder))

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract product to path:%s" % folder)

        # keep list of content: no
        # self.contentList = []
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
            print(" ## product content[%d]:'%s'" % (n, name))
            dest = "%s/%s" % (self.EO_FOLDER, name)

            if name.lower().endswith(TIFF_SUFFIX):
                if self.debug != 0:
                    print(" #### found a tif:'%s'" % name)
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
                    print(" #### found metadata file:'%s'" % name)
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

            print("   content[%s] EO_FOLDER item path:%s" % (n, name))
            # self.contentList.append(name)

            n += 1
        tar.close()

        print((" #### extract done; TifMap:%s" % self.TifMap))
        print((" #### metadata file:%s" % self.metadataFile))
        print((" #### quality file:%s" % self.QUALITY_FILE))
        print((" #### thermal file:%s" % self.THERMAL_FILE))
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
        met.setMetadataPair(metadata.METADATA_TRACK, '0%s' % kj[0:3])
        met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, '0%s' % kj[0:3])
        met.setMetadataPair(metadata.METADATA_FRAME, '0%s' % kj[3:6])
        met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, '0%s' % kj[3:6])

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

                if processInfo is not None:
                    processInfo.addLog("##### remove non ESA acq station:'%s'" % stationOk)
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
        print((" @@@@ extractOneMetadataGroup for group:%s" % group))
        groupMapping = allXmlMapping[group]
        start, stop = groupDoc.getGroupByPath(group)
        print(" @@##@@ PRODUCT_PARAMETERS for group '%s': start line:%s; stop line:%s" % (group, start, stop))
        n = 0
        for item in list(groupMapping.keys()):
            keyName = groupMapping[item]
            print((" - extracting metadata key: %s" % item))
            aValue = 'NOT-FOUND'
            for i in range(start, stop):
                aLine = groupDoc.getLine(i)
                # print("  @@ look for info[%s]='%s' key='%s' at line index:%s. Line:%s" % (n, item, keyName, i, aLine))
                if aLine.find(keyName) >= 0:
                    aValue = aLine.split('=')[1].strip().replace('"', '')
                    print(" -> %s %s found" % (item, keyName))
                    break
            print(" --> info[%s]=%s: %s" % (n, item, aValue))
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
            print((" #### footprint non reversed:%s" % footprint))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("verifyFootprint step 0 '%s' error: %s; %s" % (footprint, exc_type, exc_obj)))
            traceback.print_exc(file=sys.stdout)
            reversed = browseIm.reverseFootprint()
            print(("verifyFootprint step 1 '%s'" % reversed))
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
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

        # date
        sd = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        st = self.metadata.getMetadataValue(metadata.METADATA_START_TIME).replace('"', '')
        if st.find('.') > 0:
            tmp = "%s.%sZ" % (st.split('.')[0], st.split('.')[1][0:3])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%s" % (sd, tmp))
        else:
            tmp = "%s.000" % st
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%s" % (sd, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%sZ" % (sd, tmp))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, sd)

    #
    #
    #
    def buildTypeCode(self, processInfo):

        level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if level == 'L1GT':
            sensorMode = 'GEO'
        elif level == 'L1TP':
            sensorMode = 'GTC'
        else:
            raise Exception("Unknown processing level:%s" % level)
        typecode = "OAT_%s_1P" % sensorMode

        if not typecode in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown typecode:'%s'" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        #
        self.metadata.addLocalAttribute("originalName", self.origName.split('.')[0])

        #
        tier = self.metadata.getMetadataValue(REF_TIER_NAME)
        self.metadata.addLocalAttribute("collectionCategory", tier)

        #
        if typecode in WITH_BOUNDINGBOX:
            self.useBbox = True
            processInfo.addLog("## has boundingBox:%s" % typecode)
            self.metadata.addLocalAttribute("boundingBox", self.browseIm.getBoundingBox())
        else:
            processInfo.addLog("## has NO boundingBox:%s" % typecode)

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
