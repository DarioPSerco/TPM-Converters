"""Worldview 1-4, or Worldview Legion product"""
import os, re, shutil, sys, traceback
from multiprocessing.managers import Value
from subprocess import call

import eoSip_converter.esaProducts.verifier as verifier

from eoSip_converter.esaProducts import browse_metadata, formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory
from xml_nodes import sipBuilder, rep_footprint


# gdal commands
GDAL_STEP_0='gdal_translate -b 3 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST1'
GDAL_STEP_1='gdal_translate -b 2 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST2'
GDAL_STEP_2='gdal_translate -b 1 -scale 0 4096 -ot byte -outsize 25% 25% @SRC @DEST3'
GDAL_STEP_3='gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
GDAL_STEP_4='gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'

REF_TYPECODES = [
    'WV6_PAN_2A', 'WV6_PAN_OR', 'WV6_PAN_MP',
    'WV1_4B__2A', 'WV1_4B__OR', 'WV1_4B__MP',
    'WV1_8B__2A', 'WV1_8B__OR', 'WV1_8B__MP',
    'WV1_PAN_2A', 'WV1_PAN_OR', 'WV1_PAN_MP',
    'WV1_S8B_2A', 'WV1_S8B_MP',
    # 'WV4_PAN_2A', 'WV4_PAN_OR', 'WV4_PAN_MP',
    # 'WV4_4B__2A', 'WV4_4B__OR', 'WV4_4B__MP',
    # 'WV4_8B__2A', 'WV4_8B__OR', 'WV4_8B__MP',
]

RESOLUTION_LIMIT = 0.1
REF_PROCESSING_LEVEL = {
    'other: LV1B',
    'other: LV2A',
    'other: LV3A', 'other: LV3D', 'other: LV3E', 'other: LV3F', 'other: LV3G', 'other: LV3X',
    'other: LV4',
    'other: Stereo1B', 'other: Stereo2A', 'other: StereoOR2A'
}

WITH_BOUNDINGBOX = ['WV6_PAN_MP', 'WV1_PAN_MP', 'WV1_4B__MP', 'WV1_8B__MP', 'WV1_S8B_MP']
METADATA_SUFFIX = "_README.XML"  # Not used?
BROWSE_SUFFIX = "-BROWSE.JPG"
TIFF_SUFFIX = ".TIF"


def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


def testResolution(aRes):
    if aRes is None:
        raise Exception("testResolution: value is None")

    if isinstance(aRes, str):
        aFloat = float(aRes)

        if aFloat < RESOLUTION_LIMIT:
            print(("##@@## resolution below limit:%s" % aRes))
            return True, '0'

        return False, aRes
    else:
        print(("testResolution: param is not str but:%s" % type(aRes)))


class Product_Worldview(Product_Directory):
    xmlMapping = {}

    # for 2) then parse subfolder file like: 010787518010_01_P001_MUL/19AUG22104421-M2AS-010787518010_01_P001.IMD
    mapping2 = {
        metadata.METADATA_DATASET_PRODUCTION_DATE: 'generationTime',
        metadata.METADATA_START_DATE_TIME: 'earliestAcqTime',
        metadata.METADATA_STOP_DATE_TIME: 'latestAcqTime',
        metadata.METADATA_SUN_ELEVATION:'meanSunEl',
        metadata.METADATA_SUN_AZIMUTH: 'maxSunAz',
        metadata.METADATA_CLOUD_COVERAGE: 'cloudCover',

        'ULLon': 'ULLon',
        'ULLat': 'ULLat',
        'URLon': 'URLon',
        'URLat': 'URLat',

        'LRLon': 'LRLon',
        'LRLat': 'LRLat',
        'LLLon': 'LLLon',
        'LLLat': 'LLLat',

        'colSpacing': 'colSpacing',
        'rowSpacing': 'rowSpacing',
        'productType': 'productType',
        'productLevel': 'productLevel',
        'imageDescriptor': 'imageDescriptor',
        'numberOfLooks': 'numberOfLooks',
        metadata.METADATA_PROCESSING_LEVEL: 'productLevel',
        metadata.METADATA_SCALE: 'productScale',
        'satId': 'satId',
        'bandId': 'bandId'
        }

    # for 3) then parse subfolder file like: 010787518010_01_P001_MUL/18NOV21054629-P3DS-011211306040_01_P001.XML
    mapping3 = {
        #'productLevel_in_imd': 'IMD/PRODUCTLEVEL'
    }

    def __init__(self, path=None):
        Product_Directory.__init__(self, path)

        # Check to see if it's a stereo product and take latest timestamp XML if so
        xml_pattern = re.compile(r'.*[0-9]{3}\.XML$', re.IGNORECASE)
        metadata_xmls = [p for p in os.listdir(self.folder) if xml_pattern.match(p)]
        if len(metadata_xmls) > 1:
            metadata_xml = sorted(metadata_xmls)[-1]  # Take latest timestamp
            self.path = self.folder + os.sep + metadata_xml
            self.origName = os.path.split(self.path)[1]
            self.folder = os.path.split(self.path)[0]
            self.parentFodler = os.path.dirname(self.folder)

        self.metadata_path = self.path
        with open(self.metadata_path, 'r') as fd:
            self.metadata_content = fd.read()

        # From metadata, determine if Worldview Legion or not
        # i.e. <SATID>LG01</SATID> if WV-Legion
        try:
            self.is_wv_legion = self.metadata_content[
                self.metadata_content.index('<SATID>') + 7 :
                self.metadata_content.index('</SATID>')
            ].strip().upper().startswith('LG')
        except ValueError:
            raise ValueError(
                "<SATID> element not found in native XML. Can't determine if WV-Legion or not"
            )

        self.preview_path = []
        self.tif_matadata_map = {} # name, path
        self.mulTilPath = None
        self.mulTifPath = None
        self.browseSourceMap = {} # name, path
        self.mulBrowsePath = None

        # the product folder, parent of the *_README.XML used as input
        self.EO_FOLDER = os.path.dirname(path)
        self.useBbox = False
        self.browseIm = None
        self.tmpSize = 0

        # GIS FILES are above the EO folder
        self.contentListGis = []

        if self.debug!=0:
            print(" init class Product_Worldview")

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

    def makeBrowses(self, processInfo):
        #if self.mulBrowsePath is None:
        #    raise Exception("No MUL browse found")

        anEosip = processInfo.destProduct

        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath="%s/%s.BI.PNG" % (processInfo.workFolder, browseName)

        if self.num_preview != 0:
            if self.mulBrowsePath is None:
                raise Exception("No MUL browse found")
            import eoSip_converter.imageUtil as imageUtil
            imageUtil.makeBrowse("PNG", self.mulBrowsePath, self.browseDestPath, transparent=False)
        else:
            if self.mulTifPath is None:
                raise Exception("No MUL tiff found")
            self.makeBrowseFromTiff(processInfo, self.mulTifPath, self.browseDestPath)

        # set AM time if needed
        anEosip.setFileAMtime(self.browseDestPath)
        processInfo.destProduct.addSourceBrowse(self.browseDestPath, [])
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
            print("browseChoiceBlock L2:%s" % (browseChoiceBlock))
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

        processInfo.addLog(" L2 browse image choice created:browseChoiceBlock=\n%s" % (browseChoiceBlock))


    #
    # GIS_FILES are in ../GIS_FILES/
    #
    def addGisFiles(self):
        gisFolder = "%s/GIS_FILES" % os.path.dirname(os.path.dirname(self.path))
        print(("## gisFolder:%s" % gisFolder))

        if os.path.exists(gisFolder):
            shapeFile = "%s/%s" % (gisFolder, self.origName.replace('.XML', '_PIXEL_SHAPE.shp'))
            print(("## shapeFile:%s" % shapeFile))
            if os.path.exists(shapeFile):
                self.contentListGis = []
                self.contentListGis.append(shapeFile)
                self.contentListGis.append(shapeFile.replace('.shp', '.prj'))
                self.contentListGis.append(shapeFile.replace('.shp', '.dbf'))
                self.contentListGis.append(shapeFile.replace('.shp', '.shx'))
                if self.debug!=0:
                    print(("GIS FILES:%s" % self.contentListGis))
            else:
                print(("## shapeFile %s doesn't exists" % shapeFile))
        else:
            print(("## gisFolder %s doesn't exists" % gisFolder))



    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug!=0:
            print(" will extact directory product '%s' to path:%s" % (self.path, folder))


        if not os.path.exists(folder):
            raise Exception("destination fodler does not exists:%s" % folder)
        if self.debug!=0:
            print(" will extact product to path:%s" % folder)


        # keep list of content
        self.contentList = []
        #
        self.num_preview=0
        #
        n = 0
        paths = os.walk(self.EO_FOLDER, topdown=False)
        paths = sorted(paths, key=lambda x: x[0])  # sort by root directory
        paths = [(_[0], _[1], sorted(_[-1])) for _ in paths]  # sort files by name (latest timestamp goes last)
        for root, dirs, files in paths:
            for name in files:
                n = n + 1
                eoFile = "%s/%s" % (root, name)
                print(" ## product content[%d]:'%s' in:%s" % (n, name, dirs))

                if name.endswith(BROWSE_SUFFIX):
                    preview_path = eoFile
                    shutil.copyfile(preview_path, "%s/%s" % (folder, name))
                    print((" ## FOUND self.preview_path=%s" % preview_path))
                    self.preview_path.append(preview_path)
                    self.browseSourceMap[name] = preview_path
                    if eoFile.find("_MUL/") > 0:
                        self.mulBrowsePath=eoFile
                    self.num_preview+=1
                elif name.endswith(TIFF_SUFFIX):
                    self.tif_matadata_map[name] = eoFile.replace(TIFF_SUFFIX, ".IMD")
                    if eoFile.find("_MUL/")>0:
                        self.mulTifPath=eoFile
                        self.mulTilPath=eoFile.replace(TIFF_SUFFIX, ".IMD")

                relPath = os.path.join(root, name)[len(self.EO_FOLDER) + 1:]
                print("   content[%s] EO_FOLDER relative path:%s" % (n, relPath))
                self.contentList.append(relPath)
                self.tmpSize += os.stat(eoFile).st_size

        print("   mulTifPath:%s" % self.mulTifPath)
        print("   mulTilPath:%s" % self.mulTilPath)
        #os._exit(1)


        #if self.num_preview == 0:
        #    self.findAndMakePreview()
        #    raise Exception("No preview image found in product")

        if self.mulTilPath is None: # look for first .IMD found
            for item in self.contentList:
                if item.endswith(".IMD"):
                    self.mulTilPath = "%s/%s" % (self.EO_FOLDER, item)
                    print((" #### first .IMD found: %s" % self.mulTilPath))
                    #os._exit(1)
                elif item.endswith(BROWSE_SUFFIX):
                    if self.mulBrowsePath is None:
                        self.mulBrowsePath = "%s/%s" % (self.EO_FOLDER, item)
                        print((" #### first BROWSE found: %s" % self.mulTilPath))
                        # os._exit(1)

        self.addGisFiles()


        print((" #### extract done; num of previews:%s" % (self.num_preview)))
        print((" ####              tif_matadata_map:%s" % self.tif_matadata_map))
        print((" ####              mulTilPath:%s" % self.mulTilPath))
        print((" ####              browseSourceMap:%s" % self.browseSourceMap))
        #os._exit(1)


    #
    #
    #
    #def findAndMakePreview(self):
    #    print("#### will search and make preview inside:%s" % self.mulTifPath)
    #    os._exit(1)


    #
    # if there is no preview browse, make one using tiff file
    #
    def makeBrowseFromTiff(self, processInfo, srcPath, destPath):
        if self.debug!=0:
            print(" createBrowseFromTiff from tiff:%s" % srcPath)
        processInfo.addLog(" createBrowseFromTiff from tiff:%s" % srcPath)

        #

        # extract 3 band, equialize
        destPathBase = self.browseDestPath.replace('.BI.PNG', '_')
        command = GDAL_STEP_0.replace('@SRC', "%s" % (srcPath))
        command1 = command.replace('@DEST1', "%s_R.tif" % (destPathBase))

        command2 = GDAL_STEP_1.replace('@SRC', "%s" % (srcPath))
        command2 = command2.replace('@DEST2', "%s_G.tif" % (destPathBase))

        command3 = GDAL_STEP_2.replace('@SRC', "%s" % (srcPath))
        command3 = command3.replace('@DEST3', "%s_B.tif" % (destPathBase))

        command4 = GDAL_STEP_3.replace('@DEST1', "%s_R.tif" % (destPathBase)).replace('@DEST2', "%s_G.tif" % (
        destPathBase)).replace('@DEST3', "%s_B.tif" % (destPathBase))
        command4 = command4.replace('@DEST4', "%s_bmerged.tif" % (destPathBase))

        command5 = "%s -transparent %s %s 0xff000000" % (
        self.stretcherAppExe, "%s_bmerged.tif" % (destPathBase), "%s_transparent.tif" % (destPathBase))

        #command6 = "%s -stretch %s %s 0.01" % (
        #self.stretcherAppExe, "%s_transparent.tif" % (destPathBase), "%s_transparent_stretched.tif" % (destPathBase))

        #command6 = "%s -stretch %s %s 0.01" % (
        #    self.stretcherAppExe, "%s_transparent.tif" % (destPathBase), self.browseDestPath)

        command6 = "%s -stretch %s %s 0.02" % (
            self.stretcherAppExe, "%s_transparent.tif" % (destPathBase), "%s_transparent_stretched.tif" % (destPathBase))

        command7 = "%s -autoBrighten %s %s 110" % (
            self.stretcherAppExe, "%s_transparent_stretched.tif" % (destPathBase), destPath)

        #commands = "%s%s%s%s%s%s%s" % (
        commands = "%s%s%s%s%s%s%s" % (
        writeShellCommand(command1, True), writeShellCommand(command2, True), writeShellCommand(command3, True),
        writeShellCommand(command4, True), writeShellCommand(command5, True), writeShellCommand(command6, True),
        writeShellCommand(command7, True),
        )

        commands = "%s\necho\necho\necho 'browse done'" % (commands)

        # make transparent
        commandFile = "%s/command_browse.sh" % (processInfo.workFolder)
        fd = open(commandFile, 'w')
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        command = "/bin/bash -i -f %s >%s/command_browse.stdout 2>&1" % (commandFile, processInfo.workFolder)
        #
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % (retval))
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % (retval))
        print(" external make browse exit code:%s" % (retval))

        #os._exit(1)



    #
    # 1) parse the self.metadata_content (like 010787518010_01_README.XML on top folder) for main info
    # 2) then parse subfolder file like: 010787518010_01_P001_MUL/19AUG22104421-M2AS-010787518010_01_P001.XML
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met is None:
            raise Exception("metadate is None")

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")


        # save metadata to workfolder for test purpose:
        destPath = "%s/%s" % (processInfo.workFolder, os.path.basename(self.path))
        shutil.copyfile(self.path, destPath)

        self.metadata = met
        self.getMetadataFromIMD(processInfo)
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)
        self.buildTypeCode(processInfo)

        # check scale:
        tmp = instrument = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        if tmp in WITH_BOUNDINGBOX:
            tmp = self.metadata.getMetadataValue(metadata.METADATA_SCALE).replace('"', '')
            if tmp != "1:12,000" and tmp != "1:50,000"  and tmp != "Custom":
                raise Exception("Invalid scale: %s" % tmp)

            if tmp == "1:12,000":
                self.metadata.setMetadataPair(metadata.METADATA_SCALE, '1:12.000 Orthorectified')
                self.metadata.addLocalAttribute("scale", '1:12.000 Orthorectified')
            elif tmp == "1:50,000":
                self.metadata.setMetadataPair(metadata.METADATA_SCALE, '1:50.000 Orthorectified')
                self.metadata.addLocalAttribute("scale", '1:50.000 Orthorectified')
            elif tmp == "Custom":
                self.metadata.addLocalAttribute("scale", tmp)


    #
    # get metadata from .IMD
    #
    def getMetadataFromIMD(self, processInfo):
        imdPath = self.mulTilPath
        if not os.path.exists(self.mulTilPath):
            print((" # looking for IMD in folder:%s" % self.mulTilPath))
            imdPath = None
            aPath = os.path.dirname(self.mulTilPath)
            for panItem in os.listdir(aPath):
                print((" ## looking for .IMD: %s" % panItem))
                if panItem.endswith(".IMD"):
                    imdPath = "%s/%s" % (aPath, panItem)
                    break

        if imdPath is None:
            raise Exception("IMD file not found for %S" % self.mulTilPath)

        with open(imdPath) as fd:
            data = fd.read()

        # save to workfolder for test purpose:
        with open("%s/%s" % (processInfo.workFolder, os.path.basename(imdPath)), 'w') as fd:
            fd.write(data)

        numBands = 0
        for item in self.mapping2:
            for line in data.split("\n"):
                if line.strip().find(self.mapping2[item])>=0:
                    value = line.split("=")[1].strip()[0:-1]
                    print((" ## found: %s=%s" %(item, value)))
                    self.metadata.setMetadataPair(item, value)

                elif line.strip().startswith("BEGIN_GROUP = BAND_"):
                    numBands += 1

        numBands = numBands / len(self.mapping2)
        self.metadata.setMetadataPair('numberOfBands', numBands)
        print((" ######## numBands:%s" % numBands))

    #
    # extract the footprint
    #
    def extractFootprint(self, processInfo):
        footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                      (
                        self.metadata.getMetadataValue("ULLat"), self.metadata.getMetadataValue("ULLon"),
                        self.metadata.getMetadataValue("LLLat"), self.metadata.getMetadataValue("LLLon"),
                        self.metadata.getMetadataValue("LRLat"), self.metadata.getMetadataValue("LRLon"),
                        self.metadata.getMetadataValue("URLat"), self.metadata.getMetadataValue("URLon"),
                        self.metadata.getMetadataValue("ULLat"), self.metadata.getMetadataValue("ULLon")
                       )

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
            print(("verifyFootprint step 1 '%s'" % (reversed)))
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
            print((" #### footprint ok from reversed:%s" % reversed))

        # Adjust accuracy of footprint to 5 decimal points
        current_footprint = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        self.metadata.setMetadataPair(
            metadata.METADATA_FOOTPRINT,
            ' '.join([f"{float(c.strip()):.5f}" for c in current_footprint.split()])
        )

        clat, clon = browseIm.calculateCenter()
        flon = float(clon)
        flat = float(clat)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, f"{flat:.5f} {flon:.5f}")

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
    def refineMetadata(self, processInfo):

        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        #
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        #print("#### start:"+start)
        #os._exit(1)
        pos = start.find('.')
        msec=".000"
        if pos > 0:
            start = start[0:pos+4] + "Z"
            msec="."+start[pos+1: pos+4]
        else:
            raise Exception("unexpected start datetime format: no .: '%s'" % start)
        print(("## START:%s" % start))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start.split("T")[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start.split("T")[1].split('.')[0] + msec)

        #
        stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME)
        pos = stop.find('.')
        pos = start.find('.')
        msec=".000"
        if pos > 0:
            start = start[0:pos+4] + "Z"
            msec="."+start[pos+1: pos+4]
        else:
            raise Exception("unexpected stop datetime format: no .: '%s'" % stop)
        print(("## STOP:%s" % stop))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split("T")[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split("T")[1].split('.')[0] + msec)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE), self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # resolution
        tmp = self.metadata.getMetadataValue("rowSpacing")
        aVal = formatUtils.EEEtoNumber(tmp)
        print(("####################### rowSpacing:%s" % aVal))

        # NEW: test only too small or not found
        changed, newRes = testResolution(aVal)
        if changed:
            processInfo.addLog(" !!!! INVALID resolution: %s; changed to: %s" % (aVal, newRes))
            self.metadata.setMetadataPair("INVALID resolution", "%s; changed to: %s" % (aVal, newRes))
            aVal = newRes  # is string
        self.metadata.setMetadataPair(metadata.METADATA_RESOLUTION, float(aVal))
        
        # from "Stereo OR2A" to 'other: Stereo OR2A'
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        levelOk = "other: %s" % tmp.replace('"', '').replace(" ", '')
        if not levelOk in REF_PROCESSING_LEVEL:
            raise Exception("Invalid processing level:'%s'" % levelOk)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, levelOk)

        # get platform id
        tmp = self.metadata.getMetadataValue('satId').replace('"', '') # like "WV02"
        if not tmp.startswith('WV') and not tmp.startswith('LG'):
            raise Exception("Invalid source product, not WV0X but: '%s'" % tmp)
        print(("#### satId: %s" % tmp))

        platform_id = str(int(tmp[-2:]))# if not self.is_wv_legion else 'L'

        if platform_id not in '123456':
            raise Exception("Invalid platform id, shall be 1,2,3,4,5, or 6. Is:'%s'" % tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform_id)

        self.metadata.setMetadataPair(
            metadata.METADATA_INSTRUMENT,
            'WorldView Legion Camera' if self.is_wv_legion else
            {'1': "WV60", '2': 'WV110', '3': 'WV110', '4': 'SpaceView-110'}[platform_id]
        )

        if not self.is_wv_legion:
            instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
            self.metadata.setMetadataPair(
                metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
                f"urn:esa:eop:WorldView:{instrument}:operationalMode"
            )
        else:
            self.metadata.setMetadataPair(
                metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
                "urn:esa:eop:WorldView:WorldView Legion:operationalMode"
            )
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, "WorldView Legion")

        # cloud coverage
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE)
        if self.metadata.valueExists(tmp):
            tmp = int(float(tmp) * 100.0)
            print(("METADATA_CLOUD_COVERAGE ok: %s" % tmp))
        else:
            print("METADATA_CLOUD_COVERAGE not present")
            tmp=-999
        self.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, tmp)

    #
    #
    #
    def buildTypeCode(self, processInfo):

        # get METADATA_PLATFORM_ID: 1, 2, 3
        platformId = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        print(("#### platformId:'%s'" % platformId))
        #os._exit(1)

        # get number of bands
        nb = self.metadata.getMetadataValue("numberOfBands")
        #if nb==8:
        #    print self.path
        #    os._exit(1)

        # get raw level, format it
        tmp = self.metadata.getMetadataValue("imageDescriptor").replace('"', '')

        level = None
        if tmp == "ORStandard2A" or tmp == "Standard2A":
            level = '2A'
        elif tmp == "StereoOR2A":
            level = 'OR'
        elif tmp == "OrthoRectified3":
            level = 'MP'
        else:
            raise Exception("unknown imageDescriptor:'%s'. num band=%s" % (tmp, nb))


        # get instrument # WV6, WV1
        instrument = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)

        # get bandID # All-S or Multi
        bandID = self.metadata.getMetadataValue("bandId").replace('"', '')
        # print "BANDID: %s" % bandID

        # switch
        sensorMode = None
        sensorOpMode = None
        usedWv = 'WV1'
        if self.is_wv_legion:
            if nb == 1:
                sensorMode = 'PAN'
                sensorOpMode = 'PAN'
            elif nb == 4 or nb == 3:
                sensorMode = '4B_'
                sensorOpMode = 'PM'
            elif nb == 8:
                sensorMode = '8B_'
                sensorOpMode = 'PM'
            else:
                raise Exception("buildTypeCode; WV Legion: invalid number of bands:'%s'" % nb)
        elif platformId[-1]=='1':
            sensorMode = 'PAN'
            sensorOpMode = 'PAN'
            usedWv = 'WV6'

        elif platformId[-1] == '2':
            if nb == 1:
                sensorMode = 'PAN'
                sensorOpMode = 'PAN'
            elif nb == 4 or nb == 3:
                sensorMode = '4B_'
                sensorOpMode = 'PM'
            elif nb == 8:
                sensorMode = '8B_'  # OR SWB for some WV3
                sensorOpMode = 'PM'
            else:
                raise Exception("buildTypeCode; platform 2: invalid number of bands:'%s'" % nb)

        elif platformId[-1]=='3':
            if nb == 1:
                sensorMode = 'PAN'
                sensorOpMode = 'PAN'
            elif nb == 4 or nb == 3:
                sensorMode = '4B_'
                sensorOpMode = 'PM'
            elif nb == 8:
                if bandID == 'All-S':
                    sensorMode = 'S8B'
                    sensorOpMode = 'SWIR'
                elif bandID == 'Multi':
                    sensorMode = '8B_'  
                    sensorOpMode = 'PM'
                else:
                    raise Exception("buildTypeCode; platform 3: bandId not correct: %s" % bandID)
            else:
                raise Exception("buildTypeCode; platform 3: invalid number of bands:'%s'" % nb)

        elif platformId[-1] in '456':
            if nb == 1:
                sensorMode = 'PAN'
                sensorOpMode = 'PAN'
            elif nb == 4 or nb == 3:
                sensorMode = '4B_'
                sensorOpMode = 'PM'
            elif nb == 8:
                sensorMode = '8B_'  # OR SWB for some WV3referenceSystemIdentifier
                sensorOpMode = 'PM'
            else:
                raise Exception(f"buildTypeCode; platform {platformId[-1]}: invalid number of bands:'{nb}'")
        else:
            raise Exception("buildTypeCode: invalid platform id:'%s'" % platformId[-1])


        if sensorMode is None:
            raise Exception("buildTypeCode: sensorMode not set")
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensorOpMode)
        typecode="%s_%s_%s" % (usedWv, sensorMode, level)

        if not typecode in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown typecode:'%s'" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        if typecode in WITH_BOUNDINGBOX:
            processInfo.addLog("## have boundingBox:%s" % typecode)

            self.useBbox = True
            bbox_str = self.browseIm.getBoundingBox()
            bbox_str = ' '.join(f"{float(c.strip()):.5f}" for c in bbox_str.split())
            self.metadata.addLocalAttribute("boundingBox", bbox_str)
        else:
            processInfo.addLog("## have NO boundingBox:%s" % typecode)

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass


    #
    #
    #
    def toString(self):
        res="path:%s" % self.path
        return res


    #
    #
    #
    def dump(self):
        res="path:%s" % self.path
        print(res)
