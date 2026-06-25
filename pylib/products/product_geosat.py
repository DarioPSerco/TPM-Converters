# -*- coding: cp1252 -*-
#
# this class represent a daimos directory product
#
#  - 
#  - 
#
#
import os
import zipfile
from subprocess import call

import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.esaProducts import browse_metadata
from eoSip_converter.esaProducts import formatUtils
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory
from xml_nodes import rep_footprint

#
#
#
GDAL_STEP_0 = 'gdal_translate -of png -outsize 25% 25% @SRC @DEST'

#
#
REF_TYPECODES = ['SL6_22P_1R', 'SL6_22P_1T', 'SL6_22P_2T', 'SL6_22S_1R', 'SL6_22S_1T', 'SL6_22S_2T', 'SL6_22T_1R',
                 'SL6_22T_1T', 'SL6_22T_2T', 'HRA_PAN_1B', 'HRA_PAN_1C', 'HRA_PS3_1B', 'HRA_PS3_1C', 'HRA_PS4_1B',
                 'HRA_PS4_1C', 'PSH', 'HRA_PSH_1B', 'HRA_PSH_1C', 'HRA_MS4_1B', 'HRA_MS4_1C', 'HRA_PM4_1B',
                 'HRA_PM4_1C', 'HRA_STP_1B', 'HRA_STP_1C']


#
#


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
class Product_Geosat(Product_Directory):
    #
    METADATA_SUFFIX = '.dim'
    PREVIEW_SUFFIX = '_QL.png'
    TIF_SUFFIX = '.tif'

    #
    xmlMapping = {metadata.METADATA_PROFILE: 'Metadata_Id/METADATA_PROFILE',
                  metadata.METADATA_START_DATE_TIME: 'Dataset_Sources/Source_Information/Scene_Source/START_TIME',
                  metadata.METADATA_STOP_DATE_TIME: 'Dataset_Sources/Source_Information/Scene_Source/STOP_TIME',
                  metadata.METADATA_START_TIME: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_TIME',
                  metadata.METADATA_START_DATE: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_DATE',
                  metadata.METADATA_RESOLUTION: 'Dataset_Sources/Source_Information/Scene_Source/PIXEL_RESOLUTION_X',
                  "METADATA_RESOLUTION_BIS": 'Dataset_Sources/Source_Information/Scene_Source/THEORETICAL_RESOLUTION',

                  metadata.METADATA_PARENT_PRODUCT: 'Dataset_Sources/Source_Information/SOURCE_ID',
                  # metadata.METADATA_PLATFORM: 'Dataset_Sources/Source_Information/Scene_Source/MISSION',
                  metadata.METADATA_PLATFORM_ID: 'Dataset_Sources/Source_Information/Scene_Source/MISSION_INDEX',
                  metadata.METADATA_INSTRUMENT: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                  metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Dataset_Sources/Source_Information/Coordinate_Reference_System/Projection_OGCWKT',
                  "METADATA_REFERENCE_SYSTEM_IDENTIFIER_BIS": 'Dataset_Sources/Source_Information/Coordinate_Reference_System/Horizontal_CS/HORIZONTAL_CS_CODE',

                  metadata.METADATA_PROCESSING_LEVEL: 'Production/PRODUCT_TYPE',
                  metadata.METADATA_PROCESSING_TIME: 'Production/DATASET_PRODUCTION_DATE',
                  metadata.METADATA_SOFTWARE_NAME: 'Production/DATASET_PRODUCER_NAME',
                  metadata.METADATA_DATASET_NAME: 'Dataset_Id/DATASET_NAME',

                  metadata.METADATA_DATA_FILE_PATH: 'Data_Access/Data_File/DATA_FILE_PATH@href',
                  metadata.METADATA_DATASET_PRODUCTION_DATE: 'Production/DATASET_PRODUCTION_DATE',

                  metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
                  metadata.METADATA_SUN_AZIMUTH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_AZIMUTH',
                  metadata.METADATA_SUN_ELEVATION: 'Dataset_Sources/Source_Information/Scene_Source/SUN_ELEVATION',
                  }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        #
        self.metadata_path = None
        self.metadata_content = None

        #
        self.preview_path = []

        #
        self.tif_path = []
        self.numberOfBrowses = 0
        self.browseSourceMap = {}

        #
        self.EXTRACTED_PATH = None

        #
        self.useBbox = True

        if self.debug != 0:
            print(" init class Product_Geosat")

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
        if self.numberOfBrowses > 0:
            self.makeBrowsesFromTifs(processInfo)
        # os._exit(1)
        # elif len(self.preview_path) > 0:
        #    self.makeBrowsesFromPreviews(processInfo)

    #
    #
    #
    def makeBrowsesFromTifs(self, processInfo):
        if self.debug != 0:
            print(" makeBrowsesFromTifs: number of browses: %s" % self.numberOfBrowses)
        processInfo.addLog(" makeBrowsesFromTifs: number of browses: %s" % self.numberOfBrowses)

        anEosip = processInfo.destProduct
        self.browseRelPath = os.path.dirname(processInfo.destProduct.folder)

        #
        allBrowseName = []
        severalBrowse = False
        if self.numberOfBrowses > 1:
            severalBrowse = True

        # self.debug=1
        # for every browse, # browse where extracted during extractToPath
        allCommands = ''
        allBrowseMade = []
        n = 0
        bn = 1
        defaultDone = False
        for browseSrcPath in self.tif_path:
            print("\n makeBrowsesFromTifs: doings n=%s: %s" % (n, browseSrcPath))
            processInfo.addLog(" makeBrowsesFromTifs: doings n=%s: %s" % (n, browseSrcPath))

            # make PNG files, set .BI.PNG for default browse
            default = False
            bName = os.path.basename(browseSrcPath)
            biX = ''
            if severalBrowse:
                if bName.find('_PAN_') > 0:
                    if not defaultDone:
                        default = True
                        defaultDone = True
                        biX = 'BID'
                    else:
                        biX = 'BI%s' % bn
                        bn += 1
                else:
                    biX = 'BI%s' % bn
                    bn += 1
            else:
                biX = 'BI'

            browseName = processInfo.destProduct.getSipProductName()
            browseDestPath = "%s/%s.%s.PNG" % (self.browseRelPath, browseName, biX)
            print(("##  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath)))
            processInfo.addLog("##  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath))

            # look if a xxx_QL.PNG exists
            possibleQlPath = "%s_QL.png" % (browseSrcPath)  # % (browseSrcPath[0:-4])
            if os.path.exists(possibleQlPath):  # use existing QL.png
                if self.debug != 0:
                    print(" makeBrowsesFromTifs: tif has a preview:%s" % possibleQlPath)
                processInfo.addLog(" makeBrowsesFromTifs: tif has a preview:%s" % possibleQlPath)

                browseName = processInfo.destProduct.getSipProductName()
                browseDestPath = "%s/%s.%s.PNG" % (self.browseRelPath, browseName, biX)

                allBrowseMade.append(browseDestPath)

            else:  # make png from tif
                if self.debug != 0:
                    print(" makeBrowsesFromTifs: tif has NO preview")
                processInfo.addLog(" makeBrowsesFromTifs: tif has NO preview")

                # reduce to 1200 max
                width, height = imageUtil.get_size_gdal(browseSrcPath)
                bigger = width
                if height > bigger:
                    bigger = height
                ratio = 1600.0 / bigger
                ratio = 100.0 * ratio
                if ratio > 100:
                    ratio = 100

                if self.debug != 0:
                    print(" makeBrowsesFromTifs: tif size: w=%s; height=%s; resize ratio:%s" % (width, height, ratio))
                processInfo.addLog(
                    " makeBrowsesFromTifs: tif size: w=%s; height=%s; resize ratio:%s" % (width, height, ratio))

                browseName = processInfo.destProduct.getSipProductName()
                browseDestPath = "%s/%s.%s.PNG" % (self.browseRelPath, browseName, biX)

                # set map browse-created -> browse source
                self.browseSourceMap[os.path.basename(browseDestPath)] = os.path.basename(browseSrcPath)

                allBrowseMade.append(browseDestPath)

                browseDestPath_0 = "%s/%s__%s__0.PNG" % (self.browseRelPath, browseName, biX)
                browseDestPath_1 = "%s/%s__%s__1.PNG" % (self.browseRelPath, browseName, biX)

                GDAL_STEP_0 = "gdal_translate -of png -outsize {}% {}% @SRC @DEST".format(ratio, ratio)
                command = GDAL_STEP_0.replace('@SRC', browseSrcPath)
                command1 = writeShellCommand(command.replace('@DEST', "%s" % (browseDestPath_0)), 1)
                command2 = writeShellCommand(
                    "%s -stretch %s %s 0.01" % (self.stretcherAppExe, browseDestPath_0, browseDestPath_1),
                    1)  # browseDestPath_1), 1)
                command3 = writeShellCommand(
                    "%s  -thresholdAlpha %s %s 0 235" % (self.stretcherAppExe, browseDestPath_1, browseDestPath),
                    1)  # browseDestPath_1), 1)

                commands = "%s\n%s\n%s\necho\necho 'browse  done'\n" % (command1, command2, command3)

                allCommands += commands
            n += 1

        # os._exit(1)

        commandFile = "%s/command_make_browse.sh" % (processInfo.workFolder)
        fd = open(commandFile, 'w')
        fd.write("""#!/bin/bash\necho starting...\n\n""")
        fd.write(allCommands)
        fd.close()

        command = "/bin/bash -i -f %s/command_make_browse.sh >%s/command_browse.stdout 2>&1" % (
            processInfo.workFolder, processInfo.workFolder)
        #
        retval = call(command, shell=True)
        retval = 0
        if self.debug != 0:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        # os._exit(1)

        for browseDestPath in allBrowseMade:
            bName = os.path.basename(browseDestPath)
            anEosip.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  browse image[%s] added: name=%s; path=%s" % (n, bName, browseDestPath))
            # set AM timne if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[browseDestPath]
            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            #
            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != 0:
                print("browseChoiceBlock:%s" % (browseChoiceBlock))
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

            processInfo.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))

    #
    #
    #
    def makeBrowsesFromPreviews(self, processInfo):

        if self.debug != 0:
            print(" makeBrowsesFromPreviews: number of browses:%s" % self.numberOfBrowses)
        processInfo.addLog(" makeBrowsesFromPreviews: number of browses:%s" % len(self.preview_path))

        anEosip = processInfo.destProduct

        #
        allBrowseName = []
        severalBrowse = False
        if self.numberOfBrowses > 1:
            severalBrowse = True

        # for every browse, # browse where extracted during extractToPath
        n = 0
        bn = 1
        defaultDone = False
        for browseSrcPath in self.preview_path:
            print("\n makeBrowsesFromPreviews: doings n=%s: %s" % (n, browseSrcPath))
            processInfo.addLog(" makeBrowsesFromPreviews: doings n=%s: %s" % (n, browseSrcPath))
            # make PNG files, set .BI.PNG for default browse
            default = False
            bName = os.path.basename(browseSrcPath)

            #
            biX = ''
            if severalBrowse:
                if bName.find('_PAN_') > 0:
                    if not defaultDone:
                        default = True
                        defaultDone = True
                        biX = 'BID'
                    else:
                        biX = 'BI%s' % bn
                        bn += 1
                else:
                    biX = 'BI%s' % bn
                    bn += 1
            else:
                biX = 'BI'

            browseName = processInfo.destProduct.getSipProductName()
            browseDestPath = "%s/%s.%s.PNG" % (self.browseRelPath, browseName, biX)
            print(("##  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath)))
            processInfo.addLog("  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath))

            # not already done?
            alreadyPresent = False
            try:
                allBrowseName.index(browseDestPath)
                processInfo.addLog("  browse image[%s] already present:  name=%s; path=%s" % (n, bName, browseDestPath))
                alreadyPresent = True
            except:
                processInfo.addLog(
                    "  browse image[%s] not already present:  name=%s; path=%s" % (n, bName, browseDestPath))
                allBrowseName.append(browseDestPath)

            if not alreadyPresent:
                #
                imageUtil.makeBrowse('PNG', browseSrcPath, browseDestPath)
                anEosip.addSourceBrowse(browseDestPath, [])
                processInfo.addLog("  browse image[%s] added: name=%s; path=%s" % (n, bName, browseDestPath))
                # set AM timne if needed
                processInfo.destProduct.setFileAMtime(browseDestPath)

                # create browse choice for browse metadata report
                bmet = anEosip.browse_metadata_dict[browseDestPath]
                if self.debug != 0:
                    print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

                reportBuilder = rep_footprint.rep_footprint()
                #
                if self.debug != 0:
                    print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
                browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                               "rep:browseReport/rep:browse/rep:footprint").strip()
                if self.debug != 0:
                    print("browseChoiceBlock:%s" % (browseChoiceBlock))
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

                processInfo.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))
                n += 1

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

        self.EXTRACTED_PATH = "%s/EO_product" % folder
        if not os.path.exists(self.EXTRACTED_PATH):
            os.makedirs(self.EXTRACTED_PATH)

        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []
        n = 0
        d = 0
        for name in z.namelist():
            n = n + 1
            if self.debug != 0:
                print("  zip content[%d]:%s" % (n, name))

            if name.endswith(self.PREVIEW_SUFFIX):
                # if self.first_preview_path is None:
                # self.first_preview_path = "%s/%s" % (self.EXTRACTED_PATH, name)
                if dont_extract != True:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    self.metadata_path = self.EXTRACTED_PATH + '/' + name
                    outfile = open(self.metadata_path, 'wb')
                    outfile.write(z.read(name))
                    outfile.close()
                self.preview_path.append("%s/%s" % (self.EXTRACTED_PATH, name))

            elif name.endswith(self.TIF_SUFFIX):
                if dont_extract != True:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    aTifPath = self.EXTRACTED_PATH + '/' + name
                    outfile = open(aTifPath, 'wb')
                    outfile.write(z.read(name))
                    outfile.close()

                    self.tif_path.append(aTifPath)

            elif name.endswith(self.METADATA_SUFFIX):
                self.metadata_content = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    self.metadata_path = self.EXTRACTED_PATH + '/' + name
                    outfile = open(self.metadata_path, 'wb')
                    outfile.write(self.metadata_content)
                    outfile.close()

            if self.debug != 0:
                print("   %s extracted at path:%s" % (name, self.EXTRACTED_PATH + '/' + name))
            if name.endswith('/'):
                d = d + 1
            self.contentList.append(name)
        z.close()
        fh.close()

        if len(self.tif_path) == 0 and len(self.num_previews) == 0:
            raise Exception("No tif or preview image found in product")

        # if len(self.tif_path) > 2:
        #    raise Exception("Too many tif images for EoSip spec: max is 2. Product has:%s" % len(self.tif_path))

        self.numberOfBrowses = len(self.tif_path)
        self.num_previews = len(self.preview_path)
        print((" ## extract done; num of previews:%s\n ## num of tif:%s\n ## preview path:%s" % (
            self.num_previews, self.numberOfBrowses, self.preview_path)))
        # os._exit(1)

    #
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met == None:
            raise Exception("metadate is None")

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # set local attributes
        met.addLocalAttribute("originalName", self.origName)

        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
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
                print("  -->%s=%s" % (field, aValue))
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        print(("metadata extracted: %s" % num_added))
        self.metadata = met

        self.refineMetadata(processInfo, helper)

        self.extractFootprint(helper, met)

        self.cutUnwantedMetadata(processInfo)

        # os._exit(1)

    #
    # extract the footprint
    #
    def extractFootprint(self, helper, met):
        footprint = ""
        nodes = []
        # helper.setDebug(1)
        # helper.getNodeByPath(None, 'Dataset_Frame', None, nodes)
        helper.getNodeByPath(None, 'Dataset_Sources/Source_Information/Source_Frame', None, nodes)

        vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
        if len(vertexList) == 0:
            raise Exception("can not find footprint vertex")

        # some product have 5 pair of coords, must skip index 2
        # self.debug=1

        #
        #
        # SL6_22S_1R Ascending is like
        #
        # 0-4    1
        #
        #
        # 3      2
        #

        n = 0
        closePoint = ""
        for node in vertexList:
            lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LON', None))
            lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
            if self.debug != 0:
                print("  ############# vertex %d: lon:%s  lat:%s" % (n, lon, lat))
            if len(footprint) > 0:
                footprint = "%s " % (footprint)
            footprint = "%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))

        #
        toks = footprint.split(" ")
        footprint = "%s %s %s %s %s %s %s %s %s %s" % (toks[0], toks[1], toks[6], toks[7],
                                                       toks[4], toks[5], toks[2], toks[3], toks[0], toks[1])
        print("  ############# footprint :%s" % footprint)

        if len(vertexList) != 4:
            raise Exception("Not 4 pair footprint but:" % len(vertexList))
            print("  ############# 5 pair footprint:%s" % footprint)
            toks = footprint.split(" ")
            footprint = "%s %s %s %s %s %s %s %s %s %s" % (toks[0], toks[1], toks[2], toks[3],
                                                           toks[6], toks[7], toks[8], toks[9],
                                                           toks[10], toks[11])
            print("  ############# 5 pair footprint corrected to 4 pair:%s" % footprint)
        else:
            print("  ############# 4 pair footprint :%s" % footprint)

        # number of nodes in footprint
        met.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (n + 1))

        # modify if product is ascending:
        if self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION) == 'ASCENDING':
            print("  ############# Ascending case")
            aFootprint = " ".join(footprint.split(' ')[4:])
            aFootprint += " "
            aFootprint += " ".join(footprint.split(' ')[2:6])
            print("  ############# Ascending case, modified footprint:%s" % aFootprint)
            footprint = aFootprint
        else:
            print("  ############# Descending case")
        # os._exit(1)

        # make sure the footprint is CCW
        # also prepare CW for EoliSa index and shopcart
        browseIm = BrowseImage()
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        print(" browse image info:\n%s" % browseIm.info())
        if not browseIm.getIsCCW():
            print("  ############# footprint NOT CCW")
            # keep for eolisa
            # met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

            # and reverse
            if self.debug != 0:
                print("############### reverse the footprint; before: %s" % (footprint))
            browseIm.reverseFootprint()
            if self.debug != 0:
                print("###############                       after: %s; colRowList:%s" % (
                browseIm.getFootprint(), browseIm.getColRowList()))
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        else:
            print("  ############# footprint CCW")
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

        # os._exit(1)

        # boundingBox is needed in the localAttributes
        met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        closedBoundingBox = "%s %s %s" % (
            browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
        met.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                            browseIm.reverseSomeFootprint(closedBoundingBox))
        print(("BOUNDINGBOX: %s" % self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)))
        # print("CLOSED BOUNDINGBOX: %s"  % self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX_CW_CLOSED))
        met.addLocalAttribute("boundingBox", self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))
        # os._exit(1)

        # only for deimos 1 L1T and L2T  + deimos 2 L1C
        # if self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID) == "1":
        #     if self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL) == "L1T" or self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL) == "L2T":
        #         met.addLocalAttribute("boundingBox", closedBoundingBox)
        # elif self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID) == "2":
        #     if self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL) == "L1C":
        #         met.addLocalAttribute("boundingBox", closedBoundingBox)
        # else:
        #     raise Exception("Invalid platform id:%s" % self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID))

        # set WRS grid
        clat, clon = browseIm.getCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, clon)
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
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo, helper):
        # get some info from dataset filename, like: DE2_PM4_L1C_000000_20191207T142412_20191207T142415_DE2_29627_6ADB
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
        toks = tmp.split("_")
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, toks[0][-1])
        if toks[0][-1] == '1':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, toks[2])
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, toks[-2])
        else:
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, toks[1])
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, toks[-2])

        # METADATA_START_DATETIME, value is like 2017-06-30T11:05:50
        # METADATA_STOP_DATETIME, value is like 2017-06-30T11:05:53
        # if METADATA_START_DATE_TIME not present, use metadata.METADATA_START_TIME + metadata.METADATA_START_TIME
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        if start is not None:
            start_tokens = start.split('T')
            print((" ############# start datetime tokens:%s" % start_tokens))
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start_tokens[0])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start_tokens[1])

            # Defining METADATA_STOP_DATE, METADATA_STOP_TIME.
            stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME)
            stop_tokens = stop.split('T')
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop_tokens[0])
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop_tokens[1])
        else:
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE,
                                          self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME,
                                          self.metadata.getMetadataValue(metadata.METADATA_START_TIME))

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # instrument can be like: SLIM-6-22
        instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        if instrument.startswith("SLIM") and len(instrument) > 4:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, "SLIM6")

        # metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER is like: PROJCS["WGS 84 / UTM zone 29N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.
        # or "METADATA_REFERENCE_SYSTEM_IDENTIFIER_BIS" like: EPSG:4326
        tmp = self.metadata.getMetadataValue(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER)
        refId = None
        if tmp is not None:
            print(("### %s\n### type:%s" % (str(tmp), type(tmp))))
            refId = str(tmp).split('"')[1]
            print(("### refId 0:%s" % refId))
        else:
            refId = self.metadata.getMetadataValue("METADATA_REFERENCE_SYSTEM_IDENTIFIER_BIS")
            print(("### refId 1:%s" % refId))

        # os._exit(1)
        self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, refId)
        # print("==> %s" % (str(tmp).split('"')[1]))
        # os._exit(1)

        # platform id
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, str(int(tmp)))

        #
        self.retrieveInfoFromQualityBlock(processInfo, helper)

        #
        self.buildTypeCode(processInfo)

        # bounding box
        # self.metadata.addLocalAttribute("boundingBox", self.browseIm.getBoundingBox())
        # self.metadata.addLocalAttribute("boundingBox", self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

    #
    #
    #
    def cutUnwantedMetadata(self, processInfo):
        # incidenceAngle only for DE1
        pid = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        if pid == "2":
            self.metadata.deleteMetadata(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE)

        # resolution for all but PM4 and STP
        # can be in PIXEL_RESOLUTION_X or THEORETICAL_RESOLUTION fields
        mode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        # print " FUCK mode:%s"% mode
        # if mode != "PM4" and mode != "STP":
        tmp = self.metadata.getMetadataValue(metadata.METADATA_RESOLUTION)
        # print "FUCK resolution 1:%s; type:%s" % (tmp, type(tmp))
        if tmp is None:
            tmp = self.metadata.getMetadataValue("METADATA_RESOLUTION_BIS")
            # print "FUCK resolution 2:%s; type:%s" % (tmp, type(tmp))
            if tmp is not None:
                self.metadata.setMetadataPair(metadata.METADATA_RESOLUTION, tmp)
            else:
                raise Exception("resolution value not found")
        # else:
        #     print "DELETE METADATA_RESOLUTION"
        #     self.metadata.deleteMetadata(metadata.METADATA_RESOLUTION)

        # orbitDirection only in DE1
        pid = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        if pid == "1":
            try:
                self.metadata.deleteMetadata(metadata.METADATA_ORBIT_DIRECTION)
            except Exception as e:
                pass
                # print  "ERROR:%s"% e.message
                # self.metadata.dump()
        # os._exit(1)

    #
    #
    #
    def retrieveInfoFromQualityBlock(self, processInfo, helper):
        pid = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)

        # look each 'Dataset_Sources/Source_Information/Quality_Assessment/
        aList = []
        aNode = helper.getFirstNodeByPath(None, 'Dataset_Sources/Source_Information/Quality_Assessment')
        print(("### Quality_Assessmentnode:%s" % aNode))
        aList = helper.getNodeChildrenByName(aNode, 'Quality_Parameter')

        # cloudCover = "-1"
        #
        orbDir = None  # note: only for DE2
        n = 0
        for item in aList:
            # print(item)
            # get QUALITY_PARAMETER_CODE node
            qpNode = helper.getFirstNodeByPath(item, 'QUALITY_PARAMETER_CODE')
            qvNode = helper.getFirstNodeByPath(item, 'QUALITY_PARAMETER_VALUE')
            pn = helper.getNodeText(qpNode)
            pv = helper.getNodeText(qvNode)

            print(("### Quality_Assessmentnode/item[%s] pn=%s" % (n, pn)))
            if pn == 'SPACEMETRIC:HEADING':  # DE1 orb dir
                print(("  # foundQuality_Assessmentnode/SPACEMETRIC:HEADING=%s" % pv))
                if pid == '1':
                    if pv.upper() == 'A':
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "ASCENDING")
                        orbDir = "ASCENDING"
                    elif pv.upper() == 'D':
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "DESCENDING")
                        orbDir = "DESCENDING"
                    else:
                        raise Exception("Invalid SPACEMETRIC:HEADING:'%s'" % pv)
                elif pid == '2':
                    if pv.find("SCENDIN") > 0:
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, pv)
                        orbDir = pv
                    else:
                        raise Exception("Invalid DE1 orbit direction value:'%s'" % pv)
                else:
                    raise Exception("Invalid platform id:'%s'" % pid)
            elif pn == 'DEIMOS-IMAGING:ORD' or pn == 'GEOSAT:ORD':  # DE2 orb dir
                print(("  # foundQuality_Assessmentnode/GEOSAT:ORD=%s" % pv))
                if pid == '1':
                    if pv.upper() == 'A':
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "ASCENDING")
                        orbDir = "ASCENDING"
                    elif pv.upper() == 'D':
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "DESCENDING")
                        orbDir = "DESCENDING"
                    else:
                        raise Exception("Invalid SPACEMETRIC:HEADING:'%s'" % pv)
                elif pid == '2':
                    if pv.find("SCENDIN") > 0:
                        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, pv)
                        orbDir = pv
                    else:
                        raise Exception("Invalid DE2 orbit direction value:'%s'" % pv)
                else:
                    raise Exception("Invalid platform id:'%s'" % pid)

            elif pn == 'DEIMOS-IMAGING:CCP' or pn == 'GEOSAT:CCP':  # DE2 cloud cover
                print(("  # foundQuality_Assessmentnode/DEIMOS-IMAGING:CCP=%s" % pv))
                if pv is None:
                    cloudCover = "-1"
                else:
                    cloudCover = pv
            n += 1
        # os._exit(1)

        print(("  # foundQuality_Assessmentnode; set cloud cover to:'%s'" % cloudCover))
        self.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, cloudCover)

        print("orbDir:%s; type:%s" % (orbDir, type(orbDir)))
        if orbDir is None:
            if pid == '2':
                raise Exception("NO orbit direction info found in DE2 product")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbDir)
        # s._exit(1)

    #
    #
    #
    def buildTypeCode(self, processInfo):
        instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        p1 = None
        if instrument == "HiRAIS":
            p1 = "HRA"
        elif instrument == "SLIM6":
            p1 = "SL6"
        else:
            raise Exception("Invalid instrument:'%s'" % instrument)

        p2 = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        p3 = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)[-2:]

        typecode = "%s_%s_%s" % (p1, p2, p3)

        if typecode not in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown type code:%s" % typecode)

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

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
