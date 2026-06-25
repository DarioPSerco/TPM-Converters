# -*- coding: cp1252 -*-
#
# this class represent a geoeye1 product
#
#  - 
#  - 
#
#
import os, re, shutil, sys, traceback

#
import eoSip_converter.xmlHelper as xmlHelper
import eoSip_converter.esaProducts.verifier as verifier

from eoSip_converter.esaProducts import browse_metadata, formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory
from xml_nodes import sipBuilder, rep_footprint


REF_TYPECODES=[
    'GIS_4B__2A', 'GIS_4B__OR', 'GIS_4B__MP'
    'GIS_PAN_OR', 'GIS_PAN_MP', 'GIS_PAN_2A'
]
RESOLUTION_LIMIT = 0.1
REF_PROCESSING_LEVEL = {
    'other: LV1B',
    'other: LV2A',
    'other: LV3A', 'other: LV3D', 'other: LV3E', 'other: LV3F', 'other: LV3G', 'other: LV3X',
    'other: LV4',
    'other: Stereo1B', 'other: Stereo2A', 'other: StereoOR2A'
}
WITH_BOUNDINGBOX = ['GIS_PAN_MP', 'GIS_4B__MP']
METADATA_SUFFIX="_README.XML"  # Not used?
BROWSE_SUFFIX="-BROWSE.JPG"
TIFF_SUFFIX=".TIF"


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
        aFloat = aRes

        if aFloat < RESOLUTION_LIMIT:
            print(("##@@## resolution bolow limit:%s" % aRes))
            return True, '0'

        return False, aRes


class Product_Geoeye1(Product_Directory):
    # for 1) parse the self.metadata_content (like 010787518010_01_README.XML on top folder) for main info
    xmlMapping_ = {  # Unused?
        metadata.METADATA_START_DATE_TIME: 'COLLECTIONSTART',
        metadata.METADATA_STOP_DATE_TIME: 'COLLECTIONSTOP',
        metadata.METADATA_SCALE: 'PRODUCTSCALE',
        metadata.METADATA_CLOUD_COVERAGE: 'CLOUDCOVER',
        metadata.METADATA_DATASET_PRODUCTION_DATE: 'MEDIACREATIONDATE',
        'NWLAT': 'NWLAT',
        'NWLONG': 'NWLONG',
        'SELAT': 'SELAT',
        'SELONG': 'SELONG'
        }

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

        'colSpacing':'colSpacing',
        'rowSpacing': 'rowSpacing',
        'productType': 'productType',
        'productLevel': 'productLevel',
        'imageDescriptor': 'imageDescriptor',
        'numberOfLooks': 'numberOfLooks',
        metadata.METADATA_PROCESSING_LEVEL: 'productLevel',
        metadata.METADATA_SCALE: 'productScale',
        'satId': 'satId'
        }

    # for 3) then parse subfolder file like: 010787518010_01_P001_MUL/18NOV21054629-P3DS-011211306040_01_P001.XML
    mapping3 = {
        'productLevel_in_imd': 'IMD/PRODUCTLEVEL'
    }

    #
    #
    #
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

        self.metadata_path = path
        with open(self.metadata_path, 'r') as fd:
            self.metadata_content = fd.read()

        self.preview_path=[]
        self.tif_matadata_map = {}  # name, path
        self.mulTilPath=None
        self.browseSourceMap={}  # name, path
        self.mulBrowsePath = None

        # the product folder, parent of the *_README.XML (or *P[0-9]{3}.XML?) used as input
        self.EO_FOLDER = os.path.dirname(self.metadata_path)
        self.useBbox = False
        self.browseIm = None
        self.tmpSize = 0
        self.contentListGis = []  # GIS FILES are above the EO folder

        if self.debug!=0:
            print(" init class Product_Geoeye1")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass


    #
    # read metadata file
    #
    def getMetadataInfo(self):
        pass

    def makeBrowses(self, processInfo):
        if self.mulBrowsePath is None:
            raise Exception("No MUL browse found")

        anEosip = processInfo.destProduct

        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath="%s/%s.BI.PNG" % (processInfo.workFolder, browseName)
        import eoSip_converter.imageUtil as imageUtil
        imageUtil.makeBrowse("PNG", self.mulBrowsePath, self.browseDestPath, transparent=True)

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
        gisFolder = "%s/GIS_FILES" % os.path.dirname(self.path)
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
            raise Exception("destination folder not exists:%s" % folder)
        if self.debug!=0:
            print(" will extract directory product '%s' to path:%s" % (self.path, folder))


        if not os.path.exists(folder):
            raise Exception("destination fodler does not exists:%s" % folder)
        if self.debug!=0:
            print(" will extract product to path:%s" % folder)


        # keep list of content
        self.contentList = []
        self.num_preview = 0
        n = 0
        file_names = []

        # In this case, the file listed LAST is the one that gets parsed for
        # metadata
        # for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):
        paths = os.walk(self.EO_FOLDER, topdown=False)
        paths = sorted(paths, key=lambda x: x[0])  # sort by root directory
        paths = [(_[0], _[1], sorted(_[-1])) for _ in paths]  # sort files by name (latest timestamp goes last)
        for root, dirs, files in paths:
            for name in files:
                file_names.append(name)
                n = n + 1
                eoFile = "%s/%s" % (root, name)
                print(" ## product content[%d]:'%s' in:%s" % (n, name, eoFile))

                if name.endswith(BROWSE_SUFFIX):
                    preview_path = eoFile
                    with open(preview_path, 'r') as fd:
                        self.preview_data = fd.read()

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
                        self.mulTilPath=eoFile.replace(TIFF_SUFFIX, ".IMD")


                relPath = os.path.join(root, name)[len(self.EO_FOLDER) + 1:]
                print("   content[%s] EO_FOLDER relative path:%s" % (n, relPath))
                self.contentList.append(relPath)
                self.tmpSize += os.stat(eoFile).st_size

        if self.num_preview == 0:
            raise Exception("No preview image found in product")

        if self.mulTilPath is None: # look for first .IMD found
            for item in self.contentList:
                if item.endswith(".IMD"):# and self.mulTilPath is None:  ## Added by SPu 04/11/2024
                    self.mulTilPath = "%s/%s" % (self.EO_FOLDER, item)
                    print((" #### first .IMD found: %s" % self.mulTilPath))

                elif item.endswith(BROWSE_SUFFIX) and self.mulBrowsePath is None:
                    self.mulBrowsePath = "%s/%s" % (self.EO_FOLDER, item)
                    print((" #### first BROWSE found: %s" % self.mulTilPath))

        self.addGisFiles()


        print((" #### extract done; num of previews:%s" % (self.num_preview)))
        print((" ####              tif_matadata_map:%s" % self.tif_matadata_map))
        print((" ####              mulTilPath:%s" % self.mulTilPath))
        print((" ####              browseSourceMap:%s" % self.browseSourceMap))


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


        # extact metadata
        """
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

        self.metadata = met
        self.getMetadataFromIMD(processInfo)
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)
        self.buildTypeCode(processInfo)

    #
    # get additional metadata from .IMD
    #
    def getMetadataFromIMD(self, processInfo):
        imdPath = self.mulTilPath
        if not os.path.exists(self.mulTilPath):
            print((" # looking for IMD in folder:%s" % self.mulTilPath))
            imdPath=None
            aPath = os.path.dirname(self.mulTilPath)
            for panItem in os.listdir(aPath):
                print((" ## looking for .IMD: %s" % panItem))
                if panItem.endswith(".IMD"):
                    imdPath = "%s/%s" % (aPath, panItem)
                    break

        #os._exit(1)
        if imdPath is None:
            raise Exception("IMD file not found for %S" % self.mulTilPath)

        with open(imdPath) as fd:
            data = fd.read()

        # save to workfolder for test purpose:
        with open("%s/%s" % (processInfo.workFolder, os.path.basename(imdPath)), 'w') as fd:
            fd.write(data)

        numBands = 0
        for item in self.mapping2:
            #print(" ## test mapping2: %s -> %s" % (item, self.mapping2[item]))
            for line in data.split("\n"):
                print((" # test line:%s" % line.strip()))
                if line.strip().find(self.mapping2[item])>=0:
                    value = line.split("=")[1].strip()[0:-1]
                    print((" ## found: %s=%s" %(item, value)))
                    self.metadata.setMetadataPair(item, value)

                elif line.strip().startswith("BEGIN_GROUP = BAND_"):
                    numBands += 1

        numBands = numBands / len(self.mapping2)
        self.metadata.setMetadataPair('numberOfBands', numBands)
        #print("numBands:%s" % numBands)
        #os._exit(1)


    #
    # get additional metadata from .XML
    #
    def getMetadataFromXML(self, processInfo):
        xmlPath = self.mulTilPath
        if os.path.exists(self.mulTilPath):
            xmlPath=None
            aPath = os.path.dirname(self.mulTilPath)
            print((" # looking for XML in folder:%s" % aPath))
            for panItem in os.listdir(aPath):
                print((" ## looking for .XML: %s" % panItem))
                if panItem.endswith(".XML"):
                    xmlPath = "%s/%s" % (aPath, panItem)
                    break

        if xmlPath is None:
            raise Exception("XML file not found for %S" % self.mulTilPath)

        print((" # xmlPath found:%s" % xmlPath))

        with open(xmlPath) as fd:
            data = fd.read()

        # save to workfolder for test purpose:
        with open("%s/%s" % (processInfo.workFolder, os.path.basename(xmlPath)), 'w') as fd:
            fd.write(data)

        # extact metadata
        helper = xmlHelper.XmlHelper()
        helper.setDebug(1)
        helper.setData(self.metadata_content)
        helper.parseData()
        num_added = 0
        for field in self.mapping3:
            if self.mapping3[field].find("@") >= 0:
                attr = self.mapping3[field].split('@')[1]
                path = self.mapping3[field].split('@')[0]
            else:
                attr = None
                path = self.mapping3[field]

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
            self.metadata.setMetadataPair(field, aValue)
            num_added = num_added + 1

        print(("metadata extracted from XML: %s" % num_added))
        os._exit(1)





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
        levelOk = "other: %s" % tmp.replace('"', '').replace(' ', '')
        if not levelOk in REF_PROCESSING_LEVEL:
            raise Exception("Invalid processing level:'%s'" % levelOk)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, levelOk)

        # check satId == GE01
        tmp = self.metadata.getMetadataValue('satId').replace('"', '')
        if tmp != 'GE01':
            raise Exception("Invalid source product, not GE01 but: '%s'" % tmp)

        # cloud cover
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

        tmp = self.metadata.getMetadataValue("imageDescriptor").replace('"', '')
        nb = self.metadata.getMetadataValue("numberOfBands")

        level = None
        if tmp == "ORStandard2A" or tmp == "Standard2A":
            level = '2A'
        elif tmp == "StereoOR2A":
            level = 'OR'
        elif tmp == "OrthoRectified3":
            level = 'MP'
        else:
            raise Exception("unknown imageDescriptor:'%s'. num band=%s" % (tmp, nb))

        sensorMode = None
        if nb==4:
            sensorMode = '4B_'
        else:
            sensorMode = 'PAN'
        if sensorMode=="PAN":
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensorMode)
        else:
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'PM')

        typecode="GIS_%s_%s" % (sensorMode, level)


        if not typecode in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown typecode:'%s'" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        #if typecode=="GIS_PAN_MP" or typecode=="GIS_4B__MP":
        #    self.useBbox=True


        if typecode in WITH_BOUNDINGBOX:
            self.useBbox = True
            processInfo.addLog("## has boundingBox:%s" % typecode)
            self.metadata.addLocalAttribute("boundingBox", self.browseIm.getBoundingBox())

            tmp = self.metadata.getMetadataValue(metadata.METADATA_SCALE).replace('"', '')
            if tmp != "1:12,000" and tmp != "1:50,000" and tmp != "Custom":
                raise Exception("Invalid scale 0: '%s'" % tmp)

            if tmp == "1:12,000": # change , into .
                self.metadata.setMetadataPair(metadata.METADATA_SCALE, '1:12.000 Orthorectified')
                self.metadata.addLocalAttribute("scale", '1:12.000 Orthorectified')
            elif tmp == "1:50,000":
                self.metadata.setMetadataPair(metadata.METADATA_SCALE, '1:50.000 Orthorectified')
                self.metadata.addLocalAttribute("scale", '1:50.000 Orthorectified')
            elif tmp == "Custom":
                self.metadata.addLocalAttribute("scale", tmp)
            #else:
            #    raise Exception("Invalid scale 1: '%s'" % tmp)
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
        res="path:%s" % self.path
        return res


    #
    #
    #
    def dump(self):
        res="path:%s" % self.path
        print(res)

