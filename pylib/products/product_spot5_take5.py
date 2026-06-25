# -*- coding: cp1252 -*-
#
# this class represent a worldview directory product
#
#  - 
#  - 
#
#
import os
import sys
import tarfile
import traceback
from subprocess import call

from . import browse_metadata
import eoSip_converter.esaProducts.verifier as verifier
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from . import product_EOSIP
from .browseImage import BrowseImage
from .product_directory import Product_Directory
from xml_nodes import sipBuilder, rep_footprint

# gdal commands
GDAL_STEP_0 = 'gdal_translate -b 3 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 2 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 1 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST3'
GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
GDAL_STEP_4 = 'gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'

#
REF_METADATA_INSTRUMENT = ["HRVIR", "HRG"]


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
#
class Product_Spot5_Take5(Product_Directory):
    # for dimap
    xmlMappingDimap = {metadata.METADATA_START_DATE: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_DATE',
                       metadata.METADATA_START_TIME: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_TIME',
                       'PARENT_IDENTIFIER_BIS': 'Dataset_Sources/Source_Information/SOURCE_ID',
                       metadata.METADATA_PROCESSING_TIME: 'Production/DATASET_PRODUCTION_DATE',
                       metadata.METADATA_PROCESSING_CENTER: 'Production/Production_Facility/PROCESSING_CENTER',
                       metadata.METADATA_SOFTWARE_NAME: 'Production/Production_Facility/SOFTWARE_NAME',
                       metadata.METADATA_SOFTWARE_VERSION: 'Production/Production_Facility/SOFTWARE_VERSION',
                       metadata.METADATA_DATASET_NAME: 'Dataset_Id/DATASET_NAME',
                       metadata.METADATA_ORBIT: 'Dataset_Sources/Source_Information/Scene_Source/Imaging_Parameters/REVOLUTION_NUMBER',
                       metadata.METADATA_PARENT_PRODUCT: 'Dataset_Sources/Source_Information/SOURCE_ID',
                       metadata.METADATA_PLATFORM: 'Dataset_Sources/Source_Information/Scene_Source/MISSION',
                       metadata.METADATA_PLATFORM_ID: 'Dataset_Sources/Source_Information/Scene_Source/MISSION_INDEX',
                       metadata.METADATA_PROCESSING_LEVEL: 'Data_Processing/PROCESSING_LEVEL',
                       metadata.METADATA_INSTRUMENT: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                       metadata.METADATA_INSTRUMENT_ID: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT_INDEX',
                       metadata.METADATA_SENSOR_NAME: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                       metadata.METADATA_SENSOR_CODE: 'Dataset_Sources/Source_Information/Scene_Source/SENSOR_CODE',
                       metadata.METADATA_DATA_FILE_PATH: 'Data_Access/Data_File/DATA_FILE_PATH@href',
                       metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
                       metadata.METADATA_VIEWING_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE',
                       metadata.METADATA_SUN_AZIMUTH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_AZIMUTH',
                       metadata.METADATA_SUN_ZENITH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_ELEVATION',
                       metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Coordinate_Reference_System/Horizontal_CS/HORIZONTAL_CS_CODE',
                       metadata.METADATA_SCENE_CENTER_LON: 'Dataset_Frame/Scene_Center/FRAME_LON',
                       metadata.METADATA_SCENE_CENTER_LAT: 'Dataset_Frame/Scene_Center/FRAME_LAT'
                       }

    # for non dimap
    xmlMappingNonDimap = {
        metadata.METADATA_START_DATE: 'HEADER/DATE_PDV',
        metadata.METADATA_PLATFORM: 'HEADER/PLATEFORM',
        metadata.METADATA_INSTRUMENT: 'HEADER/SENSOR',
        metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'HEADER/MODE',
        metadata.METADATA_PROCESSING_LEVEL: 'HEADER/LEVEL',
        metadata.METADATA_PROCESSING_TIME: 'HEADER/DATE_PROD',
        metadata.METADATA_SOFTWARE_VERSION: 'HEADER/VERSION',
        # metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER:'GEOMETRY/PROJECTION',
        metadata.METADATA_RESOLUTION: 'GEOMETRY/RESOLUTION',

        #
        metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'RADIOMETRY/ANGLES/THETA_V',
        metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: 'RADIOMETRY/ANGLES/PHI_V',
        metadata.METADATA_SUN_AZIMUTH: 'RADIOMETRY/ANGLES/PHI_S',
        metadata.METADATA_SUN_ZENITH: 'RADIOMETRY/ANGLES/THETA_S',

        #  CTN_HISTORY/TASK/TASK/INPUT_PRODUCTS/FILE where PLUGIN_ASKED = ORTHO
        # metadata.METADATA_PRODUCT_SOURCE:'CTN_HISTORY/TASK/TASH',
        'ZONE_GEO': 'HEADER/ZONE_GEO',
        'NB_COLS': 'NB_COLS',
        'NB_ROWS': 'NB_ROWS'
    }

    #
    # look like there are several type of products:
    # - dimap like (all N1C?)
    #   browse ends up with PREVIEW.JPG, but too small: redo them from the ,tif file
    #
    # - non dimap one:
    #  several (or one?) xxx.TIF + xxx.xml + MASK & QUICKLOOKS folders
    #
    METADATA_NON_DIMAP = '.xml'
    TIF_NON_DIMAP_SUFIX = '.TIF'
    PREVIEW_NON_DIMAP_SUFFIX = '.jpg'
    PREVIEW_NON_DIMAP_FOLVER = '/QUICKLOOKS/'

    # dimap case
    METADATA_DIMAP_SUFIX = 'METADATA.DIM'
    PREVIEW_DIMAP_SUFFIX = 'PREVIEW.JPG'
    TIF_DIMAP_SUFIX = '.tif'

    #
    REF_TYPECODES = ['HRI_XS__1A',
                     'HRI_XS__1C',
                     'HRI_XS__2A',
                     'HRG_XS__1A',
                     'HRG_XS__1C',
                     'HRG_XS__2A']

    #
    INSTRUMENT_HRG = 'HRG'
    INSTRUMENT_HRVIR = 'HRVIR'
    REF_INSTRUMENT_NAMES = [INSTRUMENT_HRVIR, INSTRUMENT_HRG]

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)

        # may have several

        # for non dimap like
        self.metNonDimapContentName = []
        self.metNonDimapContent = []

        # for dimap like
        self.isDimap = None
        self.metDimapContentName = []
        self.metDimapContent = []

        # for non dimap like
        self.previewNonDimapContentName = []
        self.previewNonDimapContent = []
        self.imageNonDimapContentName = []  # name of the .TIF file(s)
        # image that are ortho ( that we wants as default ?? )
        self.imageIsOrtho = {}
        self.previewMosaic = None
        self.previewDefault = None

        # for dimap like
        self.previewContentName = []
        self.previewContent = []

        # make browse counter
        self.buildBrowseCounter = 0

        self.isN1c = None
        self.isL2 = None
        self.hasAlreadyBrowse = None

        if self.debug != 0:
            print(" init class Product_Spot5_Take5")

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
    # if there is no preview browse, make one using tiff file
    #
    def makeBrowseFromTiff(self, processInfo, srcPath, destPath):
        if self.debug != 0:
            print(" createBrowseFromTiff from tiff:%s" % srcPath)
        processInfo.addLog(" createBrowseFromTiff from tiff:%s" % srcPath)

        #

        # extract 3 band, equialize
        destPathBase = self.browseDestPath.replace('.PNG', '_')
        command = GDAL_STEP_0.replace('@SRC', "%s/%s" % (processInfo.workFolder, srcPath))
        command1 = command.replace('@DEST1', "%s_R.tif" % destPathBase)

        command2 = GDAL_STEP_1.replace('@SRC', "%s/%s" % (processInfo.workFolder, srcPath))
        command2 = command2.replace('@DEST2', "%s_G.tif" % destPathBase)

        command3 = GDAL_STEP_2.replace('@SRC', "%s/%s" % (processInfo.workFolder, srcPath))
        command3 = command3.replace('@DEST3', "%s_B.tif" % destPathBase)

        command4 = GDAL_STEP_3.replace('@DEST1', "%s_R.tif" % destPathBase).replace('@DEST2', "%s_G.tif" % (
            destPathBase)).replace('@DEST3', "%s_B.tif" % destPathBase)
        command4 = command4.replace('@DEST4', "%s_bmerged.tif" % destPathBase)

        command5 = "%s -transparent %s %s 0xff000000" % (
            self.stretcherAppExe, "%s_bmerged.tif" % destPathBase, "%s_transparent.tif" % destPathBase)

        # command6 = "%s -stretch %s %s 0.01" % (
        # self.stretcherAppExe, "%s_transparent.tif" % (destPathBase), "%s_transparent_stretched.tif" % (destPathBase))

        # command6 = "%s -stretch %s %s 0.01" % (
        #    self.stretcherAppExe, "%s_transparent.tif" % (destPathBase), self.browseDestPath)

        command6 = "%s -stretch %s %s 0.02" % (
            self.stretcherAppExe, "%s_transparent.tif" % destPathBase, "%s_transparent_stretched.tif" % destPathBase)

        command7 = "%s -autoBrighten %s %s 110" % (
            self.stretcherAppExe, "%s_transparent_stretched.tif" % destPathBase, destPath)

        # commands = "%s%s%s%s%s%s%s" % (
        commands = "%s%s%s%s%s%s%s" % (
            writeShellCommand(command1, True), writeShellCommand(command2, True), writeShellCommand(command3, True),
            writeShellCommand(command4, True), writeShellCommand(command5, True), writeShellCommand(command6, True),
            writeShellCommand(command7, True),
        )

        commands = "%s\necho\necho\necho 'browse %s done'" % (commands, self.buildBrowseCounter)

        # make transparent
        commandFile = "%s/command_browse_%s.sh" % (processInfo.workFolder, self.buildBrowseCounter)
        fd = open(commandFile, 'w')
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        command = "/bin/bash -i -f %s >%s/command_browse_%s.stdout 2>&1" % (
        commandFile, processInfo.workFolder, self.buildBrowseCounter)
        #
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse %s exit code:%s" % (self.buildBrowseCounter, retval))
        if retval != 0:
            raise Exception("Error generating browse %s, exit coded:%s" % (self.buildBrowseCounter, retval))
        print(" external make browse %s exit code:%s" % (self.buildBrowseCounter, retval))

        # os._exit(1)

    #
    # 2020: changes
    # - L2A: use the jpeg(s) found during the extract
    # - N1C:
    #
    def makeBrowses(self, processInfo):

        if self.hasAlreadyBrowse:
            todo = {}

            if self.previewMosaic is not None and self.previewDefault is not None:
                todo[".BI.PNG"] = self.previewMosaic
                todo[".BID.PNG"] = self.previewDefault
            elif self.previewMosaic is not None or self.previewDefault is not None:
                if self.previewMosaic is not None:
                    todo[".BI.PNG"] = self.previewMosaic
                if self.previewDefault is not None:
                    todo[".BI.PNG"] = self.previewDefault
            else:
                raise Exception("self.hasAlreadyBrowse is True but no browse or mosaic found")

            if self.debug != 0:
                print(" makeBrowses for L2: number:%s; items:%s" % (len(todo), todo))
            processInfo.addLog("- makeBrowses for L2: number:%s; items:%s" % (len(todo), todo))
            anEosip = processInfo.destProduct
            # browse path
            browseRelPath = os.path.dirname(anEosip.folder)
            browseName = processInfo.destProduct.getEoProductName()

            n = 0
            for ext in todo:
                if self.debug != 0:
                    print(" makeBrowses for L2: browse[%s]; ext:%s; name:%s" % (n, ext, todo[ext]))
                processInfo.addLog("- makeBrowses for L2: browse[%s]; ext:%s; name:%s" % (n, ext, todo[ext]))
                self.browseDestPath = "%s/%s%s" % (processInfo.workFolder, browseName, ext)

                # shutil.copy("%s/%s" % (self.EXTRACTED_PATH, todo[ext]), self.browseDestPath)
                # from jpeg to PNG
                imageUtil.makeBrowse("PNG", "%s/%s" % (self.EXTRACTED_PATH, todo[ext]),
                                     self.browseDestPath)  # ,  transparent=True)

                # set AM time if needed
                processInfo.destProduct.setFileAMtime(self.browseDestPath)
                self.previewNonDimapContentName.append(self.browseDestPath)
                anEosip.addSourceBrowse(self.browseDestPath, [])
                processInfo.addLog(" browse image for L2 added: name=%s; path=%s" % (browseName, self.browseDestPath))

                # create browse choice for browse metadata report
                bmet = anEosip.browse_metadata_dict[self.browseDestPath]
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
                n += 1
            return

        # didn't got jpeg preview from native product; use tif
        if self.debug != 0:
            print(" makeBrowses non-L2: number of browses:%s" % len(self.previewNonDimapContentName))
        processInfo.addLog("- makeBrowses non-L2: number of browses:%s" % len(self.previewNonDimapContentName))
        n = 0
        anEosip = processInfo.destProduct
        # browse path 
        browseRelPath = os.path.dirname(anEosip.folder)

        # they can be no browse
        if len(self.previewNonDimapContentName) == 0:
            if len(self.imageNonDimapContentName) == 0:
                raise Exception("got no .TIF image to make the browse")
            else:
                print(" makeBrowses non-L2: number of tif file:%s" % len(self.imageNonDimapContentName))
                processInfo.addLog("- makeBrowses non-L2: number of tif file:%s" % len(self.imageNonDimapContentName))

            if self.debug != 0:
                print(" makeBrowse non-L2s: no browse case; make one from the tif file:%s" % \
                      self.imageNonDimapContentName[0])
            processInfo.addLog(
                "- makeBrowses non-L2: no browse case; make one from the tif file:%s" % self.dimapTifName)

            browseName = processInfo.destProduct.getEoProductName()
            self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)
            self.makeBrowseFromTiff(processInfo, self.imageNonDimapContentName[0], self.browseDestPath)
            # set AM time if needed
            processInfo.destProduct.setFileAMtime(self.browseDestPath)
            self.previewNonDimapContentName.append(self.browseDestPath)
            anEosip.addSourceBrowse(self.browseDestPath, [])
            processInfo.addLog(" browse image[%s] added: name=%s; path=%s" % (n, browseName, self.browseDestPath))

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[self.browseDestPath]
            if self.debug != 0:
                print("###\n###\n### non-L2 BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            #
            if self.debug != 0:
                print("###\n###\n### non-L2 BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != 0:
                print("browseChoiceBlock non-L2:%s" % browseChoiceBlock)
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

            processInfo.addLog(
                " browse non-L2 image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))

        else:
            # they can be one or two browse p + MS
            severalBrowse = False
            index = -1
            if len(self.previewNonDimapContentName) > 1:
                severalBrowse = True

            # for every browse, # browse where extracted during extractToPath
            for bName in self.previewNonDimapContentName:
                # make PNG files, set .BI.PNG for default browse
                browseSrcPath = "%s/../%s" % (anEosip.folder, bName)
                if self.debug != 0:
                    print(" makeBrowses non-L2: making browse[%s/%s] from src:%s" % (
                    n, len(self.previewNonDimapContentName), browseSrcPath))
                processInfo.addLog("- makeBrowses non-L2: making browse[%s/%s] from src:%s" % (
                n, len(self.previewNonDimapContentName), browseSrcPath))

                default = False
                browseName = processInfo.destProduct.getEoProductName()
                #
                if severalBrowse:
                    if bName.find('ORTHO') > 0:
                        browseDestPath = "%s/%s.BID.PNG" % (browseRelPath, browseName)
                        self.imageIsOrtho[os.path.basename(browseDestPath)] = True
                    else:
                        index += 1
                        if index == 0:
                            browseDestPath = "%s/%s.BI.PNG" % (browseRelPath, browseName)
                            self.imageIsOrtho[os.path.basename(browseDestPath)] = False
                        else:
                            browseDestPath = "%s/%s.BI%s.PNG" % (browseRelPath, browseName, index)
                            self.imageIsOrtho[os.path.basename(browseDestPath)] = False
                else:
                    browseDestPath = "%s/%s.BI.PNG" % (browseRelPath, browseName)
                    self.imageIsOrtho[os.path.basename(browseDestPath)] = False

                # test add several same browse name: shoulf be forbidden
                browseDestPath = "%s/%s.BI.PNG" % (browseRelPath, browseName)
                self.imageIsOrtho[os.path.basename(browseDestPath)] = False

                #
                imageUtil.makeBrowse('PNG', browseSrcPath, browseDestPath)
                # set AM time if needed
                processInfo.destProduct.setFileAMtime(browseDestPath)
                anEosip.addSourceBrowse(browseDestPath, [])
                processInfo.addLog(" non-L2 browse image[%s] added: name=%s; path=%s" % (n, bName, browseDestPath))

                # create browse choice for browse metadata report
                bmet = anEosip.browse_metadata_dict[browseDestPath]
                if self.debug != 0:
                    print("###\n###\n### BUILD non-L2 BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

                reportBuilder = rep_footprint.rep_footprint()
                #
                if self.debug != 0:
                    print("###\n###\n### BUILD non-L2 BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
                browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                               "rep:browseReport/rep:browse/rep:footprint").strip()
                if self.debug != 0:
                    print("browseChoiceBlock non-L2:%s" % browseChoiceBlock)
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

                processInfo.addLog(
                    " non-L2 browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))
                n += 1

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.EXTRACTED_PATH = folder

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)
        tar = tarfile.open(self.path, 'r')

        # keep list of content
        self.contentList = []
        # 
        n = 0
        # TODO : implements spot5 take5 test
        self.isSpot5Take5 = True
        self.dimapTifName = None
        for tarinfo in tar:
            n = n + 1
            name = tarinfo.name
            if self.debug != 0:
                print("  test tar content[%d]:'%s'" % (n, name))

            # keep metadata and preview data
            if name.find(self.METADATA_DIMAP_SUFIX) >= 0:  # metadata dimap
                self.metDimapContentName.append(name)
                if self.debug != 0:
                    print("   metDimapContentName:%s" % name)
                fd = tar.extractfile(tarinfo)
                data = fd.read()
                fd.close()
                print("   metDimapContent length:%s" % len(data))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metDimapContent.append(data)

            elif name.find(self.METADATA_NON_DIMAP) >= 0:  # metadata non dimap
                # maybe several .xml (for browse), keep the .xml
                pos = name.find('.', 1)
                if name[pos:] == self.METADATA_NON_DIMAP:
                    self.metNonDimapContentName.append(name)
                    if self.debug != 0:
                        print("   metContentName:%s" % name)
                    fd = tar.extractfile(tarinfo)
                    data = fd.read()
                    fd.close()
                    print("   metContent length:%s" % len(data))
                    if dont_extract != True:
                        parent = os.path.dirname(folder + '/' + name)
                        if not os.path.exists(parent):
                            os.makedirs(parent)
                        outfile = open(folder + '/' + name, 'wb')
                        outfile.write(data)
                        outfile.close()
                    self.metNonDimapContent.append(data)
                    if self.isDimap is not None:
                        raise Exception(
                            "try to set isDimap true but is not empty; is already assigned to:%s" % self.isDimap)
                    self.isDimap = True
                else:
                    print('discard .xml:%s' % name)

            elif name.find(self.PREVIEW_DIMAP_SUFFIX) >= 0:  # preview for dimap
                self.previewContentName.append(name)
                if self.debug != 0:
                    print("   preview2ContentName:%s" % name)
                fd = tar.extractfile(tarinfo)
                data = fd.read()
                fd.close()
                print("   preview2Content length:%s" % len(data))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.previewContent.append(data)

            elif name.find(self.PREVIEW_NON_DIMAP_FOLVER) > 0:  # xxx/QUICKLOOKS/xxx
                print(" ####  NON_DIMAP QUICKLOOKS folder:%s" % name)
                self.hasAlreadyBrowse = True
                if name.lower().endswith(self.PREVIEW_NON_DIMAP_SUFFIX):
                    basename = os.path.basename(name)
                    if basename.startswith("Mosaic"):
                        self.previewMosaic = name
                        print(" ####  NON_DIMAP previewMosaic:%s" % (
                            name))
                        fd = tar.extractfile(tarinfo)
                        data = fd.read()
                        fd.close()
                        print("   preview2Content length:%s" % len(data))
                        if dont_extract != True:
                            parent = os.path.dirname(folder + '/' + name)
                            if not os.path.exists(parent):
                                os.makedirs(parent)
                            outfile = open(folder + '/' + name, 'wb')
                            outfile.write(data)
                            outfile.close()
                    else:
                        self.previewDefault = name
                        print(" ####  NON_DIMAP previewDefault:%s" % (
                            name))
                        fd = tar.extractfile(tarinfo)
                        data = fd.read()
                        fd.close()
                        print("   preview2Content length:%s" % len(data))
                        if dont_extract != True:
                            parent = os.path.dirname(folder + '/' + name)
                            if not os.path.exists(parent):
                                os.makedirs(parent)
                            outfile = open(folder + '/' + name, 'wb')
                            outfile.write(data)
                            outfile.close()

                    if 1 == 2:
                        self.previewContentName.append(name)
                        if self.debug != 0:
                            print("   previewContentName:%s" % name)
                        fd = tar.extractfile(tarinfo)
                        data = fd.read()
                        fd.close()
                        print("   previewContent length:%s" % len(data))
                        if dont_extract != True:
                            parent = os.path.dirname(folder + '/' + name)
                            if not os.path.exists(parent):
                                os.makedirs(parent)
                            outfile = open(folder + '/' + name, 'wb')
                            outfile.write(data)
                            outfile.close()
                        self.previewContent.append(data)

            # they maybe several tif, like in a MASK folder
            elif name.find(self.TIF_DIMAP_SUFIX) >= 0:  # tif for dimap
                # if self.DEBUG!=0:
                print(" ####  DIMAP tif name:%s" % name)

                if name.lower().find('mask') >= 0:
                    # if self.DEBUG != 0:
                    print(" ####   this is a DIMAP MASK tif")
                else:
                    print(" ####   this is the DIMAP REAL tif")
                    fd = tar.extractfile(tarinfo)
                    data = fd.read()
                    fd.close()
                    print("   tifContent length:%s" % len(data))
                    if dont_extract != True:
                        parent = os.path.dirname(folder + '/' + name)
                        if not os.path.exists(parent):
                            os.makedirs(parent)
                        outfile = open(folder + '/' + name, 'wb')
                        outfile.write(data)
                        outfile.close()
                    self.dimapTifName = name

            elif name.find(self.TIF_NON_DIMAP_SUFIX) >= 0:  # tifs for non dimap
                # if self.DEBUG!=0:
                print(" ####  NON_DIMAP tif name:%s" % name)

                if name.lower().find('mask') >= 0:
                    # if self.DEBUG != 0:
                    print(" ####   this is a NON_DIMAP MASK tif")
                else:
                    print(" ####   this is the NON_DIMAP REAL tif")
                    fd = tar.extractfile(tarinfo)
                    data = fd.read()
                    fd.close()
                    print("   tifContent length:%s" % len(data))
                    if dont_extract != True:
                        parent = os.path.dirname(folder + '/' + name)
                        if not os.path.exists(parent):
                            os.makedirs(parent)
                        outfile = open(folder + '/' + name, 'wb')
                        outfile.write(data)
                        outfile.close()
                    self.imageNonDimapContentName.append(name)

            self.contentList.append(name)

        tar.close()

        if not self.isSpot5Take5:
            raise Exception("is not a spot5 take5 product")
        # os._exit(0)

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    #
    #
    def extractMetadataDimap(self, met, processInfo):

        if len(self.metDimapContent) != 1:
            raise Exception("wrong number of dimap metadata files:%s" % len(self.metDimapContent))

        helper = xmlHelper.XmlHelper()
        helper.setData(self.metDimapContent[0])
        helper.parseData()

        metNum = 0
        for field in self.xmlMappingDimap:
            if self.xmlMappingDimap[field].find("@") >= 0:
                attr = self.xmlMappingDimap[field].split('@')[1]
                path = self.xmlMappingDimap[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMappingDimap[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  dimap metnum[%s] -->%s=%s" % (metNum, field, aValue))

            met.setMetadataPair(field, aValue)
            metNum += 1

        # os._exit(1)

        # refine
        self.refineMetadataDimap(helper, processInfo)

    #
    # refine the metadata
    #
    def refineMetadataDimap(self, xmlHelper, processInfo):
        # build product versions
        # versionOk = self.buildVersion(processInfo) # get 3 digit from software version
        softVersion = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        versionOk = formatUtils.buildSip3DigitVersion(softVersion, "_V")
        counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        if counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:
            counter = '1'
        fullVersionOk = "%s%s" % (versionOk, counter)
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, fullVersionOk)  # in the sip package name
        if self.debug != 0:
            print(" ## versions; productVersion:%s%s" % (fullVersionOk, counter))
        self.metadata.setMetadataPair("VERSION_OK", versionOk)

        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # fix processing time: from 2008-10-01T14:52:01.000000 to 2008-10-01T14:52:01Z
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if tmp.find(' ') > 0:
            tmp = tmp.replace(' ', 'T')
        tmp1 = formatUtils.removeMsecFromDateTimeString(tmp)
        if tmp != tmp1:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)

        # set start
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        pos = tmp.find('.')
        if pos > 0:
            tmp = "%sZ" % tmp[0:pos]
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp)
        else:
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp)

        # == stop
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, tmp)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set scene center coordinate
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LON)
        tmp = formatUtils.EEEtoNumber(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, tmp)
        tmp1 = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LAT)
        tmp1 = formatUtils.EEEtoNumber(tmp1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, tmp1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (tmp1, tmp))

        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        # test that platform id is 4 or 5
        if tmp != '4' and tmp != '5':
            raise Exception("invalid platform id:%s" % tmp)
        if tmp == '4':
            self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, 'Spot4 Take5')
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, 'Spot5 Take5')

        # set typecode
        instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        # correction for HRVIR1/2 not in EoSip spec
        if instrument.startswith(self.INSTRUMENT_HRVIR):
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, self.INSTRUMENT_HRVIR)
        # correction for HRG1/2 not in EoSip spec
        if instrument.startswith(self.INSTRUMENT_HRG):
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, self.INSTRUMENT_HRG)

        # if instrument not in self.REF_INSTRUMENT_NAMES:
        #    raise Exception("invalid instrument:'%s' VS ref:%s" % (instrument, self.REF_INSTRUMENT_NAMES))

        if 1 == 2:
            mode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
            if not self.metadata.valueExists(mode):
                raise Exception("no METADATA_SENSOR_OPERATIONAL_MODE")
            if len(mode) < 3:
                mode = formatUtils.rightPadString(mode, 3, '_')

        # by eosip spec:
        mode = 'XS_'

        level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if 1 == 2:
            if tmp == '1A':
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 1C')
                if instrument == 'HRG':
                    tmp = "%s_%s_1C" % (instrument, mode)
                    self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
                elif instrument == 'HRV':
                    tmp = "HRI_%s_2A" % mode
                    self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
                else:
                    raise Exception("invalid sensor:%s" % instrument)
            else:
                raise Exception("invalid processing level: %s" % tmp)

        # new:
        typeCode = None
        if instrument == 'HRG':
            typeCode = "HRG_XS__%s" % level
        elif instrument == 'HRV':
            typeCode = "HRI_XS__%s" % level

        if typeCode not in self.REF_TYPECODES:
            raise Exception("invalid typecode:'%s'" % typeCode)

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typeCode)

        # adjust METADATA_SENSOR_OPERATIONAL_MODE to spec: X
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'X')

        #
        self.extractFootprintDimap(xmlHelper)

    #
    #
    #
    def extractMetadataNonDimap(self, met, processInfo):
        # raise Exception("NON DIMAP DISABLED !!")

        #
        metNum = 0
        numMetcontent = 0
        for metContent in self.metNonDimapContent:
            n = 0
            for item in self.metNonDimapContentName:
                if n == numMetcontent:
                    break
            if self.debug != 0:
                print("\n########## numMetcontent:%s; name:%s" % (numMetcontent, item))

            # extact metadata
            helper = xmlHelper.XmlHelper()
            helper.setData(metContent)
            helper.parseData()

            # get fields
            resultList = []
            op_element = helper.getRootNode()
            num_added = 0

            n = 0
            for field in self.xmlMappingNonDimap:
                if self.debug != 0:
                    print("######################## do non dimap field[%s]:%s" % (n, field))
                if self.xmlMappingNonDimap[field].find("@") >= 0:
                    attr = self.xmlMappingNonDimap[field].split('@')[1]
                    path = self.xmlMappingNonDimap[field].split('@')[0]
                else:
                    attr = None
                    path = self.xmlMappingNonDimap[field]

                aData = helper.getFirstNodeByPath(None, path, None)

                if aData == None:
                    aValue = None
                else:
                    if attr == None:
                        aValue = helper.getNodeText(aData)
                    else:
                        aValue = helper.getNodeAttributeText(aData, attr)

                if self.debug != 0:
                    print("  non dimap metnum[%s] -->%s=%s" % (metNum, field, aValue))

                met.setMetadataPair(field, aValue)
                num_added = num_added + 1
                n += 1
                metNum += 1

            numMetcontent += 1

        # refine
        self.refineMetadataNonDimap(helper, processInfo)

    #
    # refine the metadata
    #
    def refineMetadataNonDimap(self, xmlHelper, processInfo):
        # build product versions
        # versionOk = self.buildVersion(processInfo) # get 3 digit from software version
        softVersion = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        versionOk = formatUtils.buildSip3DigitVersion(softVersion, "_V")
        counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        if counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:
            counter = '1'
        fullVersionOk = "%s%s" % (versionOk, counter)
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, fullVersionOk)  # in the sip package name
        if self.debug != 0:
            print(" ## versions; productVersion:%s%s" % (fullVersionOk, counter))
        self.metadata.setMetadataPair("VERSION_OK", versionOk)

        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        #
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, 0)

        # set start/stop date time to production data which is like: 2015-07-16 08:53:39
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos]
        # start
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, tmp.split(' ')[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp.split(' ')[1])

        # processing time
        # fix processing time: from 2008-10-01T14:52:01.000000 to 2008-10-01T14:52:01Z
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if tmp.find(' ') > 0:
            tmp = tmp.replace(' ', 'T')
        tmp1 = formatUtils.removeMsecFromDateTimeString(tmp)
        if tmp != tmp1:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)

        # self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)
        # tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        # if tmp[-1] != 'Z':
        #    tmp = '%sZ' % tmp
        # tmp = tmp.replace(' ', 'T')
        # tmp1 = formatUtils.removeMsecFromDateTimeString(tmp)
        # self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)

        # stop date + time position
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE,
                                      self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME,
                                      self.metadata.getMetadataValue(metadata.METADATA_START_TIME))
        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # separate flatform id from platform name that is like: SPOT5
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        # test that platform id is 4 or 5
        if tmp[-1] != '4' and tmp[-1] != '5':
            raise Exception("invalid platform id:%s" % tmp[-1])
        if tmp[-1] == '4':
            self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, 'Spot4 Take5')
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, 'Spot5 Take5')
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, tmp[-1])
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, tmp[0:-1])

        # processing level are : N2A or N1_TUILE

        # set also typecode
        instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        # correction for HRVIR1/2 not in EoSip spec
        if instrument.startswith(self.INSTRUMENT_HRVIR):
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, self.INSTRUMENT_HRVIR)
        # correction for HRG1/2 not in EoSip spec
        elif instrument.startswith(self.INSTRUMENT_HRG):
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, self.INSTRUMENT_HRG)
        else:
            raise Exception("METADATA_INSTRUMENT not known:'%s'" % instrument)

        #
        if len(instrument) > 3:
            instrument = instrument[0:3]
        # if instrument not in self.REF_INSTRUMENT_NAMES:
        #    raise Exception("invalid instrument:'%s' VS ref:%s" % (instrument, self.REF_INSTRUMENT_NAMES))

        mode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if len(mode) < 3:
            mode = formatUtils.rightPadString(mode, 3, '_')
        if mode != 'XS_':
            raise Exception("invalid instrument mode:%s" % mode)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if tmp == 'N2A':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 2A')
            if instrument == 'HRG':
                tmp = "%s_%s_2A" % (instrument, mode)
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
            elif instrument == 'HRV':
                tmp = "HRI_%s_2A" % mode
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
            else:
                raise Exception("invalid sensor:%s" % instrument)
        elif tmp == 'N1_TUILE':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 1C')
            if instrument == 'HRG':
                tmp = "%s_%s_1C" % (instrument, mode)
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
            elif instrument == 'HRV':
                tmp = "HRI_%s_1C" % mode
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp)
            else:
                raise Exception("invalid sensor:%s" % instrument)
        else:
            raise Exception("invalid processing level: %s" % tmp)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        if tmp not in self.REF_TYPECODES:
            raise Exception("invalid typecode:%s" % tmp)

        # adjust METADATA_SENSOR_OPERATIONAL_MODE to spec: X
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'X')

        #
        self.extractFootprintNonDimap(xmlHelper)

    #
    #
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met == None:
            raise Exception("metadate is None")

        self.metadata = met

        # use what contains the metadata file
        # in the two cases
        if len(self.metNonDimapContent) == 0:
            if len(self.metDimapContent) == 0:
                raise Exception("no metadata to be parsed")
            self.extractMetadataDimap(met, processInfo)
        else:
            self.extractMetadataNonDimap(met, processInfo)

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # set local attributes
        met.addLocalAttribute("originalName", self.origName)
        # geographic zone
        # # change: add country and town > 5000
        # met.addLocalAttribute("geographicZone", met.getMetadataValue('ZONE_GEO'))

    #
    # 
    #
    def buildTypeCode(self):
        return

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass

    #
    #
    #
    def extractFootprintDimap(self, helper):

        #
        # look like (spot5 only?) vertex are ordered:
        #  0+1 --- 1
        #  |       |
        #  3 ----- 2
        #

        footprint = ""
        rowCol = ""
        nodes = []
        # helper.setDebug(1)
        helper.getNodeByPath(None, 'Dataset_Frame', None, nodes)
        if len(nodes) == 1:
            vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
            if len(vertexList) == 0:
                raise Exception("can not find footprint vertex")

            n = 0
            closePoint = None
            for node in vertexList:
                lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LON', None))
                lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
                if self.debug != 0:
                    print("  ############# vertex %d: lon:%s  lat:%s" % (n, lon, lat))
                if len(footprint) > 0:
                    footprint = "%s " % footprint
                footprint = "%s%s %s" % (footprint, lat, lon)

                if n == 0:
                    closePoint = "%s %s" % (lat, lon)

                n = n + 1
            footprint = "%s %s" % (footprint, closePoint)
            print("footprint:%s" % footprint)

            #
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            clat, clon = browseIm.getCenter()
            # not if lat > 70 degree
            if abs(float(lat)) < 70:
                try:
                    verifier.verifyFootprint(footprint, True)  # all descending
                    self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                    self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS NOT REVERESED")
                    print((" #### verifyFootprint footprint non reversed:%s" % footprint))
                except:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    print((" # verifyFootprint step 0 '%s' error: %s; %s" % (footprint, exc_type, exc_obj)))
                    traceback.print_exc(file=sys.stdout)
                    reversed = browseIm.reverseFootprint()
                    print((" # verifyFootprint step 1 '%s'" % reversed))
                    verifier.verifyFootprint(reversed, True)
                    self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
                    self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
                    print((" #### verifyFootprint footprint ok from reversed:%s" % reversed))
            else:
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # os._exit(1)

            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)

            # 1A have no boudingBox
            level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            if level != "1A":
                self.metadata.addLocalAttribute("boundingBox", browseIm.boondingBox)

            flat = float(clat)
            flon = float(clon)
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
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                          formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                          formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))
        else:
            raise Exception("footprint node not found")

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprintNonDimap(self, helper):
        #
        hgx = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/HGX', None))
        hgy = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/HGY', None))

        hdx = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/HDX', None))
        hdy = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/HDY', None))

        bgx = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/BGX', None))
        bgy = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/BGY', None))

        bdx = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/BDX', None))
        bdy = helper.getNodeText(helper.getFirstNodeByPath(None, 'WGS84/BDY', None))

        footprint = "%s %s %s %s %s %s %s %s %s %s" % (hgy, hgx, bgy, bgx, bdy, bdx, hdy, hdx, hgy, hgx)
        # print "hgx:%s  hgy:%s    hdx:%s  hdy:%s    hdx:%s  hdy:%s    hdx:%s  hdy:%s" % (hgx, hgy, hgx, hgy, bgx, bgy, bdx, bdy)
        print("footprint:%s" % footprint)

        #
        browseIm = BrowseImage()
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        try:
            verifier.verifyFootprint(footprint, True)  # all descending
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            self.metadata.setMetadataPair("#### FOOTPRINT", "FOOTPRINT IS NOT REVERESED")
        except:
            reversed = browseIm.reverseFootprint()
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("#### FOOTPRINT", "FOOTPRINT IS REVERESED")

        clat, clon = browseIm.getCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)

        # 1A have no boudingBox
        level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if level != "1A":
            self.metadata.addLocalAttribute("boundingBox", browseIm.boondingBox)

        flat = float(clat)
        flon = float(clon)
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
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

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
