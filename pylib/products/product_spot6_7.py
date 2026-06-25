# -*- coding: cp1252 -*-
#
# this class represent a spot 6-7 directory product
#
#  - 
#  - 
#
#
import os
import sys
# import logging
import zipfile

from . import browse_metadata
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
# from product import Product
from .product_directory import Product_Directory
from xml_nodes import rep_footprint
from xml_nodes import sipBuilder

# import re
# from subprocess import call,Popen, PIPE


# for verification
REF_TYPECODE = {'NAO_P___1A',
                'NAO_P___2_',
                'NAO_P___3_',
                'NAO_MS__1A',
                'NAO_MS__2_',
                'NAO_MS__3_',
                'NAO_PMS_1A',
                'NAO_PMS_2_',
                'NAO_PMS_3_',
                'NAO_P_S_1A',
                'NAO_P_S_2_',
                'NAO_P_S_3_'}


class Product_Spot6_7(Product_Directory):
    # for spot6/7
    xmlMapping = {metadata.METADATA_START_DATE: 'Dataset_Sources/Source_Identification/Strip_Source/IMAGING_DATE',
                  metadata.METADATA_START_TIME: 'Dataset_Sources/Source_Identification/Strip_Source/IMAGING_TIME',
                  metadata.METADATA_PLATFORM: 'Dataset_Sources/Source_Identification/Strip_Source/MISSION',
                  metadata.METADATA_PLATFORM_ID: 'Dataset_Sources/Source_Identification/Strip_Source/MISSION_INDEX',
                  metadata.METADATA_INSTRUMENT_ID: 'Dataset_Sources/Source_Identification/Strip_Source/INSTRUMENT_INDEX',
                  #
                  metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Geometric_Data/Use_Area/Located_Geometric_Values/Acquisition_Angles/INCIDENCE_ANGLE_ALONG_TRACK',
                  metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: 'Geometric_Data/Use_Area/Located_Geometric_Values/Acquisition_Angles/INCIDENCE_ANGLE_ACROSS_TRACK',
                  metadata.METADATA_SUN_AZIMUTH: 'Geometric_Data/Use_Area/Located_Geometric_Values/Solar_Incidences/SUN_AZIMUTH',
                  metadata.METADATA_SUN_ELEVATION: 'Geometric_Data/Use_Area/Located_Geometric_Values/Solar_Incidences/SUN_ELEVATION',
                  #
                  metadata.METADATA_PROCESSING_TIME: 'Product_Information/Delivery_Identification/PRODUCTION_DATE',
                  #
                  'SPECTRAL_PROCESSING': 'Processing_Information/Product_Settings/SPECTRAL_PROCESSING',
                  'DATASET_TYPE': 'Dataset_Identification/DATASET_TYPE'}

    # to be removed from xml if value is None
    optionnal_nodes = [metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE,
                       metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE,
                       metadata.METADATA_SUN_AZIMUTH,
                       metadata.METADATA_SUN_ELEVATION]

    NO_NUMERIC_VALUE = '-999999'

    # for spot6/7
    METADATA_PREFIX = 'DIM_SPOT'
    PREVIEW_PREFIX = 'PREVIEW_SPOT'

    # for bundle. We use the MS metadata. NO: unlnown product are pleiades, not spot6/7
    # METADATA_PREFIX_BUNDLE='DIM_PHR1B_MS_'
    # PREVIEW_PREFIX_BUNDLE='PREVIEW_PHR1B_MS_'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        # may have several images
        self.metContentName = []
        self.metContent = []
        self.previewContentName = []
        self.previewContent = []
        # preview that are MS (multispectral)
        self.previewIsMs = {}
        if self.debug != 0:
            print(" init class Product_Spot6_7")

    #
    # read matadata file
    #
    def getMetadataInfo(self, index=0):
        pass

    #
    #
    #
    def makeBrowses(self, processInfo):
        if self.debug != 0:
            print(" makeBrowses: number of browses:%s" % len(self.previewContentName))
        processInfo.addLog(" makeBrowses: number of browses:%s" % len(self.previewContentName))
        n = 0
        anEosip = processInfo.destProduct
        # browse path 
        browseRelPath = os.path.dirname(anEosip.folder)

        # they can be one or two browse p + MS
        #
        # new: they may be several scene p in some products, which may result in several time the sane browseName
        # ==> keep only the first
        #
        allBrowseName = []
        severalBrowse = False
        if len(self.previewContentName) > 1:
            severalBrowse = True
        # for every browse, # browse where extracted during extractToPath
        for bName in self.previewContentName:
            # make PNG files, set .BI.PNG for default browse
            browseSrcPath = "%s/../%s" % (anEosip.folder, bName)
            default = False
            #
            if severalBrowse:
                if bName.find('_MS_') > 0:
                    default = True
            if default:
                browseName = processInfo.destProduct.getSipProductName()
                browseDestPath = "%s/%s.BID.PNG" % (browseRelPath, browseName)
                self.previewIsMs[os.path.basename(browseDestPath)] = True
            else:
                browseName = processInfo.destProduct.getSipProductName()
                browseDestPath = "%s/%s.BI.PNG" % (browseRelPath, browseName)
                self.previewIsMs[os.path.basename(browseDestPath)] = False

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

                processInfo.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))
                n += 1

    #
    # extract the spot 6 7 interresting piece in working folder:
    # - metadata xml
    # - preview images
    #
    def extractToPath(self, folder=None, dont_extract=False):
        self.debug = 1
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.EXTRACTED_PATH = folder

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)
        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []
        # 
        n = 0
        self.isSpot6 = False
        self.isSpot7 = False
        self.isSpot = False
        self.isBundle = False
        self.hasBundleP = False
        self.hasBundleMS = False
        for name in z.namelist():
            basename = os.path.basename(name)
            n = n + 1
            if self.debug != 0:
                print("  extract[%d]:%s" % (n, name))
            # if dont_extract!=True:
            #    outfile = open(folder+'/'+name, 'wb')
            #    outfile.write(z.read(name))
            #    outfile.close()

            # keep metadata and preview data
            # if basename.startswith(self.METADATA_PREFIX) or  basename.startswith(self.METADATA_PREFIX_BUNDLE): # metadata
            if basename.startswith(self.METADATA_PREFIX):  # metadata
                if self.debug != 0:
                    print("   metadata file:%s" % basename)
                self.metContentName.append(name)
                if self.debug != 0:
                    print("   metContentName:%s" % name)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metContent.append(data)

            # elif (basename.startswith(self.PREVIEW_PREFIX) or  basename.startswith(self.PREVIEW_PREFIX_BUNDLE)) and basename.upper().endswith('.JPG'): # preview
            elif basename.startswith(self.PREVIEW_PREFIX) and basename.upper().endswith('.JPG'):  # preview
                if self.debug != 0:
                    print("   preview file:%s" % basename)
                self.previewContentName.append(name)
                if self.debug != 0:
                    print("   previewContentName:%s" % name)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.previewContent.append(data)

            #
            self.contentList.append(name)

            # SPOT 6/7 test
            if name.find('/IMG_SPOT6') >= 0:
                self.isSpot6 = True
                self.isSpot = True
            elif name.find('/IMG_SPOT7') >= 0:
                self.isSpot7 = True
                self.isSpot = True
            elif 1 == 2:  # bundle test: NO, is pleiades
                basename = os.path.basename(name)
                if basename.startswith('IMG_PHR1B_MS_'):
                    self.hasBundleMS = True
                    if self.debug != 0:
                        print("   hasBundleMS True; basename=%s" % basename)
                    if self.hasBundleP:
                        self.isBundle = True
                elif basename.startswith('IMG_PHR1B_P_'):
                    self.hasBundleP = True
                    if self.debug != 0:
                        print("   hasBundleP True; basename=%s" % basename)
                        if self.hasBundleMS:
                            self.isBundle = True

        z.close()
        fh.close()

        if not self.isSpot:
            raise Exception("is not a spot6/7 product")
            # if not self.isBundle:
            # raise Exception("is not a spot6/7 nor bundle product")
            # else:
            #    print " is a bundle product"
        else:
            print(" is a spot6/7 product")

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")

        # they may be several DIMAP files, two in byndle.
        # metadata for US may differ in SPECTRAL_PROCESSING and DATASET_TYPE
        metNum = 0
        self.SPECTRAL_PROCESSING = {}
        self.DATASET_TYPE = {}
        numMetContent = 0
        for metContent in self.metContent:
            # metContent=self.metContent[0]

            # extact metadata
            helper = xmlHelper.XmlHelper()
            # helper.setDebug(1)
            helper.setData(metContent)
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
                # print "@@@@@@@@@@@@@@@@@ field:%s node:%s type:%s" % (field, aData, type(aData))
                if aData == None:
                    aValue = None
                else:
                    if attr == None:
                        aValue = helper.getNodeText(aData)
                    else:
                        aValue = helper.getNodeAttributeText(aData, attr)

                if self.debug != 0:
                    print(" metnum[%s,%s] -->%s=%s; type:%s" % (metNum, num_added, field, aValue, type(aValue)))

                if field == 'SPECTRAL_PROCESSING':
                    self.SPECTRAL_PROCESSING[aValue] = aValue
                elif field == 'DATASET_TYPE':
                    self.DATASET_TYPE[aValue] = aValue

                met.setMetadataPair(field, aValue)
                num_added = num_added + 1

            metNum += 1

            footprint, colrow = self.extractFootprint2(helper)
            if self.debug != 0:
                print(" footprint for metadata[%s]:%s" % (numMetContent, footprint))

            numMetContent += 1

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        met.addLocalAttribute("originalName", self.origName)

        self.metadata = met

        # refine
        self.refineMetadata(helper)

    #
    # refine the metada
    #
    def refineMetadata(self, xmlHelper):
        # processing software version: not in all products
        # use setting one if not found
        software = xmlHelper.getFirstNodeByPath(None, 'Processing_Information/Production_Facility/SOFTWARE', None)
        if software == None:
            # raise Exception('can not get software node in metadata')
            print(" @@@@@@@@@@@@@@@@@@@@@@@@@ no processing software found in metadata")

        # stop date + time position
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, formatUtils.removeMsecFromTimeString(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE,
                                      self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, formatUtils.removeMsecFromTimeString(tmp))
        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # processing date
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        tmp1 = formatUtils.removeMsecFromDateTimeString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)
        # print "%s;%s" % (tmp, tmp1)

        # get grid from lineage
        # find strip id like: <COMPONENT_PATH href="LINEAGE/STRIP_DS_SPOT6_201306031242000_FR1_FR1_SE1_SE1_W041S07_03332_DIM.XML"/>
        # NO: get it from 'Dataset_Sources/Source_Identification/SOURCE_ID'
        path = 'Dataset_Content/Dataset_Components/Component/COMPONENT_PATH'
        resultList = []

        # NEW:
        lonLat = None
        path = 'Dataset_Sources/Source_Identification/SOURCE_ID'
        xmlHelper.getNodeByPath(None, path, None, resultList)
        if self.debug != 0:
            print("component paths; len=%s" % len(resultList))
        for item in resultList:
            value = xmlHelper.getNodeText(item)
            if value.startswith('DS_SPOT'):
                lonLat = value.split('_')[7]

        # if lineage==None:
        if lonLat == None:
            raise Exception('can not find SPOT lonlat')
        if self.debug != 0:
            print(" lonLat:%s" % lonLat)

        # NEW: get it from scene center bellow in extract footprint
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, lonLat[4:])
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, lonLat[0:4])
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, '000')
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, '000')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, lonLat[4:])
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, lonLat[0:4])

        # get version from: <DATASET_NAME version="1.0">ORT_SPOT7_20140917_102524900_000</DATASET_NAME> line 12
        # no : use Processing_Information/Production_Facility/SOFTWARE attribute version
        # path='Dataset_Identification/DATASET_NAME'
        path = 'Processing_Information/Production_Facility/SOFTWARE'
        resultList = []
        xmlHelper.getNodeByPath(None, path, None, resultList)
        if 1 == 2 and len(resultList) == 1:  # force else
            version = xmlHelper.getNodeAttributeText(resultList[0], 'version')
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ print SOFTWARE VERSION:%s" % version)
            fileVersion = version.replace('.', '')
            if len(fileVersion) > 3:
                fileVersion = fileVersion[0:3]
            elif len(fileVersion) < 3:
                fileVersion = formatUtils.leftPadString(fileVersion, 3, '0')

            counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
            if counter == sipBuilder.VALUE_NONE:
                counter = '1'
            self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                          "%s%s" % (fileVersion, counter))  # in the sip package name
            self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)  # in the MD
            if self.debug != 0:
                print(" version:%s; fileVersion:%s" % (version, fileVersion))
        else:
            # raise Exception("can not retrieve dataset version")
            # default to zero
            fileVersion = '000'
            version = '000'
            counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
            if counter == sipBuilder.VALUE_NONE:
                counter = '1'
            self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                          "%s%s" % (fileVersion, counter))  # in the sip package name
            self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)  # in the MD
            if self.debug != 0:
                print(" version defaulted to:%s; fileVersion:%s" % (version, fileVersion))

        # set second to 00
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        toks = tmp.split(':')
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, "%s:%s:00" % (toks[0], toks[1]))

        # remove optionnal nodes
        for item in self.optionnal_nodes:
            tmp = self.metadata.getMetadataValue(item)
            # print "test for optional node:%s=%s; type:%s" % (item, tmp, type(tmp))
            if tmp is None:  # or tmp == sipBuilder.VALUE_NOT_PRESENT:
                # self.metadata.deleteMetadata(item)
                # print " removed optional node:%s=%s; type:%s" % (item, tmp, type(item))
                self.metadata.setMetadataPair(item, self.NO_NUMERIC_VALUE)
                print(" set optional node:%s=%s; type:%s to NO_NUMERIC_VALUE:%s" % (
                item, tmp, type(item), self.NO_NUMERIC_VALUE))
        # sys.exit(-1)

        #
        self.buildTypeCode()

        #
        self.extractFootprint(xmlHelper)

    #
    # NAO_P___1A (SPOT 6-7 Panchromatic primary)  ==> only spectral proceesing 'P'
    # NAO_P___3_ (SPOT 6-7 Panchromatic ortho)    ==> only spectral proceesing 'P'
    # NAO_MS__1A (SPOT 6-7 Multispectral primary) ==> only spectral proceesing 'MS'
    # NAO_MS__3_ (SPOT 6-7 Multispectral ortho)   ==> only spectral proceesing 'MS'
    # NAO_PMS_1A (SPOT 6-7 PanSharpened primary)  ==> only spectral proceesing 'PMS'
    # NAO_PMS_3_ (SPOT 6-7 PanSharpened ortho)    ==> only spectral proceesing 'PMS'
    # NAO_P_S_1A (SPOT 6-7 Bundle primary)        ==> spectral proceesing 'P' + 'MS'
    #
    def buildTypeCode(self):
        sensor = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)

        for key in list(self.SPECTRAL_PROCESSING.keys()):
            print('%s TODO SPECTRAL_PROCESSING:%s' % (self.origName, self.SPECTRAL_PROCESSING[key]))
        for key in list(self.DATASET_TYPE.keys()):
            print('%s TODO DATASET_TYPE:%s' % (self.origName, self.DATASET_TYPE[key]))

        n = 0
        for key in list(self.SPECTRAL_PROCESSING.keys()):
            value = self.SPECTRAL_PROCESSING[key]
            print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ self.SPECTRAL_PROCESSING key[%s]:%s; value:%s' % (n, key, value))
            print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ self.SPECTRAL_PROCESSING key:%s; value:%s' % (key, value))
            self.processInfo.infoKeeper.addInfo("%s_SPECTRAL_PROCESSING" % self.origName, value)
            n += 1

        mode = '##'
        if len(list(self.SPECTRAL_PROCESSING.keys())) == 2:  # should be p + MS
            if 'P' in self.SPECTRAL_PROCESSING and 'MS' in self.SPECTRAL_PROCESSING:
                mode = 'P_S'
            else:
                raise Exception("strange spectral_mode pair: %s %s" % (
                list(self.SPECTRAL_PROCESSING.keys())[0], list(self.SPECTRAL_PROCESSING.keys())[1]))
        else:
            mode = list(self.SPECTRAL_PROCESSING.keys())[0]

        if len(mode) < 3:
            mode = formatUtils.rightPadString(mode, 3, '_')

            # there is also products with RASTER_PROJECTED
        tmp = self.metadata.getMetadataValue('DATASET_TYPE')
        plevel = '##'
        if tmp == 'RASTER_ORTHO':
            plevel = '3_'
        elif tmp == 'RASTER_SENSOR':
            plevel = '1A'
        elif tmp == 'RASTER_PROJECTED':
            plevel = '2_'

        # if sensor is None or mode=='##' or plevel=='##':
        #    raise Exception("buildTypeCode; unknown sensor:%s or mode:%s or plevel:%s" % (sensor, mode, plevel))

        typecode = "%s_%s_%s" % (sensor, mode, plevel)
        if not typecode in REF_TYPECODE:
            raise Exception(
                "buildTypeCode; unknown typecode:%s; sensor:%s, mode:%s, plevel:%s" % (typecode, sensor, mode, tmp))

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        if plevel == '3_':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, '3')
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, plevel)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper):
        # print "Workfolder:%s" % self.processInfo.workFolder
        n = 0
        for browsePath in self.previewContentName:
            if self.debug != 0:
                print(" extractFootprint, use preview[%s]:%s" % (n, browsePath))
            # get preview resolution
            try:
                imw, imh = imageUtil.get_image_size("%s/%s" % (self.processInfo.workFolder, browsePath))
                if self.debug != 0:
                    print("  extractFootprint preview image size: w=%s; h=%s" % (imw, imh))
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" ERROR getting preview image size:%s %s\n%s" % (exc_type, exc_obj, exc_tb))
                raise Exception("ERROR getting preview image size")

            # get product image resolution
            tmpNodes = []
            helper.getNodeByPath(None, 'Raster_Data/Raster_Dimensions', None, tmpNodes)
            if len(tmpNodes) == 1:
                ncols = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NCOLS', None))
                nrows = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NROWS', None))
                if self.debug != 0:
                    print("  extractFootprint product image size: w=%s; h=%s" % (ncols, nrows))
            else:
                raise Exception("ERROR getting Raster_Dimensions")

            rcol = int(ncols) / imw
            rrow = int(nrows) / imh
            # print "  ############# ratio product/preview: rcol=%s; rrow=%s" % (rcol, rrow)

            footprint = ""
            rowCol = ""
            nodes = []
            # helper.setDebug(1)
            helper.getNodeByPath(None, 'Dataset_Content/Dataset_Extent', None, nodes)
            k = 0
            if len(nodes) == 1:
                # get vertex
                vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
                if len(vertexList) == 0:
                    raise Exception("can not find footprint vertex")

                closePoint = ""
                closeRowCol = ""
                for node in vertexList:  # CW first top left
                    lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'LON', None))
                    lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'LAT', None))
                    row = helper.getNodeText(helper.getFirstNodeByPath(node, 'ROW', None))
                    col = helper.getNodeText(helper.getFirstNodeByPath(node, 'COL', None))
                    if self.debug != 0:
                        print("  ############# vertex %d: lon:%s  lat:%s  row:%s  col:%s" % (k, lon, lat, row, col))
                    if len(footprint) > 0:
                        footprint = "%s " % footprint
                    if len(rowCol) > 0:
                        rowCol = "%s " % rowCol
                    footprint = "%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                    okRow = int(row) / rcol
                    okCol = int(col) / rrow
                    if row == '1':
                        okRow = 1
                    if col == '1':
                        okCol = 1
                    rowCol = "%s%s %s" % (rowCol, okRow, okCol)

                    if k == 0:
                        closePoint = "%s %s" % (formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                        closeRowCol = "%s %s" % (okRow, okCol)
                    k += 1

            else:
                raise Exception("ERROR getting Dataset_Extent")

            footprint = "%s %s" % (footprint, closePoint)
            rowCol = "%s %s" % (rowCol, closeRowCol)
            if self.debug != 0:
                print("  ############# footprint=%s; rowCol=%s" % (footprint, rowCol))

            # number of nodes in footprint
            self.metadata.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (k + 1))

            # get center
            tmpNodes = []
            helper.getNodeByPath(None, 'Dataset_Content/Dataset_Extent/Center', None, tmpNodes)
            if 1 == 2 and len(tmpNodes) == 1:  # force calculate center
                clon = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'LON', None))
                clat = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'LAT', None))
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
            else:
                # raise Exception("ERROR getting Dataset_Extent/Center")
                browseIm = BrowseImage()
                browseIm.setFootprint(footprint)
                clat, clon = browseIm.calculateCenter()
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
                self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))

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

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            browseIm.setColRowList(rowCol)
            if self.debug != 0:
                print("browseIm:%s" % browseIm.info())
            if not browseIm.getIsCCW():
                # keep for eolisa
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

                # and reverse
                if self.debug != 0:
                    print("############### reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
                browseIm.reverseFootprint()
                if self.debug != 0:
                    print("###############             after;%s; colRowList:%s" % (
                    browseIm.getFootprint(), browseIm.getColRowList()))
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, browseIm.getColRowList())
            else:
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, rowCol)

                # reverse for eolisa
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

            # boundingBox is needed in the localAttributes ONLY for level 3_
            level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            # raise Exception("processing level:'%s'" % level)
            if level == '3':
                self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
                closedBoundingBox = "%s %s %s" % (
                browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
                self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                                              browseIm.reverseSomeFootprint(closedBoundingBox))

                if not self.metadata.localAttributeExists("boundingBox"):
                    self.metadata.addLocalAttribute("boundingBox",
                                                    self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

            n += 1

        return footprint, rowCol

    #
    # extract the footprint: for testint purpose, on avery possible metadata
    #
    def extractFootprint2(self, helper):
        n = 0
        for browsePath in self.previewContentName:
            if self.debug != 0:
                print(" extractFootprint2, use preview[%s]:%s" % (n, browsePath))
            # get preview resolution
            try:
                imw, imh = imageUtil.get_image_size("%s/%s" % (self.processInfo.workFolder, browsePath))
                if self.debug != 0:
                    print("  extractFootprint2 preview image size: w=%s; h=%s" % (imw, imh))
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" ERROR getting preview image size:%s %s\n%s" % (exc_type, exc_obj, exc_tb))
                raise Exception("ERROR getting preview image size")

            # get product image resolution
            tmpNodes = []
            helper.getNodeByPath(None, 'Raster_Data/Raster_Dimensions', None, tmpNodes)
            if len(tmpNodes) == 1:
                ncols = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NCOLS', None))
                nrows = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NROWS', None))
                if self.debug != 0:
                    print("  extractFootprint2 product image size: w=%s; h=%s" % (ncols, nrows))
            else:
                raise Exception("ERROR getting Raster_Dimensions")

            rcol = int(ncols) / imw
            rrow = int(nrows) / imh
            # print "  ############# ratio product/preview: rcol=%s; rrow=%s" % (rcol, rrow)

            footprint = ""
            rowCol = ""
            nodes = []
            # helper.setDebug(1)
            helper.getNodeByPath(None, 'Dataset_Content/Dataset_Extent', None, nodes)
            k = 0
            if len(nodes) == 1:
                # get vertex
                vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
                if len(vertexList) == 0:
                    raise Exception("can not find footprint vertex")

                closePoint = ""
                closeRowCol = ""
                for node in vertexList:  # CW first top left
                    lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'LON', None))
                    lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'LAT', None))
                    row = helper.getNodeText(helper.getFirstNodeByPath(node, 'ROW', None))
                    col = helper.getNodeText(helper.getFirstNodeByPath(node, 'COL', None))
                    if self.debug != 0:
                        print("  ############# vertex %d: lon:%s  lat:%s  row:%s  col:%s" % (k, lon, lat, row, col))
                    if len(footprint) > 0:
                        footprint = "%s " % footprint
                    if len(rowCol) > 0:
                        rowCol = "%s " % rowCol
                    footprint = "%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                    okRow = int(row) / rcol
                    okCol = int(col) / rrow
                    if row == '1':
                        okRow = 1
                    if col == '1':
                        okCol = 1
                    rowCol = "%s%s %s" % (rowCol, okRow, okCol)

                    if k == 0:
                        closePoint = "%s %s" % (formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                        closeRowCol = "%s %s" % (okRow, okCol)
                    k += 1

            else:
                raise Exception("ERROR getting Dataset_Extent")

            footprint = "%s %s" % (footprint, closePoint)
            rowCol = "%s %s" % (rowCol, closeRowCol)
            if self.debug != 0:
                print("  ############# footprint=%s; rowCol=%s" % (footprint, rowCol))

            # number of nodes in footprint
            # self.metadata.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (k+1))

            # get center
            tmpNodes = []
            helper.getNodeByPath(None, 'Dataset_Content/Dataset_Extent/Center', None, tmpNodes)
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            clat, clon = browseIm.calculateCenter()
            # self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
            # self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
            # self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))

            flat = float(clat)
            flon = float(clon)
            mseclon = abs(int((flon - int(flon)) * 1000))
            mseclat = abs(int((flat - int(flat)) * 1000))
            if flat < 0:
                flat = "S%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
            else:
                flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
            if flon < 0:
                flon = "W%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
            else:
                flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
            # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
            # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
            # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,  formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
            # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            browseIm.setColRowList(rowCol)
            if self.debug != 0:
                print("browseIm:%s" % browseIm.info())
            if not browseIm.getIsCCW():
                # keep for eolisa
                # self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

                # and reverse
                if self.debug != 0:
                    print("############### reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
                browseIm.reverseFootprint()
                if self.debug != 0:
                    print("###############             after;%s; colRowList:%s" % (
                    browseIm.getFootprint(), browseIm.getColRowList()))

            n += 1

        return footprint, rowCol

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
