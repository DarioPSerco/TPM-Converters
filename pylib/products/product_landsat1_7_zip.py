# -*- coding: cp1252 -*-
#
# this class represent a landsat EoSip product, that will be upgraded to EoSip spec 2.0
#
#
import os
import random
import sys
import traceback
import zipfile

from . import base_metadata
#
import eoSip_converter.xmlHelper as xmlHelper
from . import eosip_product_helper
# import browse_metadata
from . import formatUtils
from . import landsat1_7_mdAdapter
from . import metadata
from . import product_EOSIP
from .browseImage import BrowseImage
# import eoSip_converter.imageUtil as imageUtil
# import eoSip_converter.geomHelper as geomHelper
from .groupedDocument import GroupedDocument
#
from .namingConvention import NamingConvention
from .product import Product
# from product_directory import Product_Directory
from xml_nodes import sipBuilder

# for verification
REF_TYPECODE = ['MSS_GEO_1P', 'MSS_GTC_1P', 'TM__GEO_1P', 'TM__GTC_1P', 'ETM_GTC_1P']
REF_PROCESSING_TYPE = ['L1G', 'L1Gt', 'L1T']
REF_ORIGINAL_FILENAME = 'LM01_L1GS_219025_20150603_19750511_FUI'
# also defined in ingester:
SRC_REF_NAME = 'LS07_RNSG_ETM_GTC_1P_19991102T094600_19991102T094629_002924_0191_0031_CC72.ZIP'

# BUMPER MODE switch date for sensor_mode
# L4 + L5 TM and L7 ETM
L5_BUMPER_MODE_SWITCH = "2002-03-01T00:00:00Z"
L7_BUMPER_MODE_SWITCH = "2007-04-01T00:00:00Z"

# scan_line_anomaly switch date.
# Landsat 7 ETM +
L7_ETM_SCAN_LINE_ANOMALY_SWITCH = "2003-05-31T00:00:00Z"


#
#
#
class Product_landsat1_7_zip(Product):
    # common to all
    LOCAL_ATTR_COMMON = ['upperLeft_Cloud_Vote', 'upperRight_Cloud_Vote', 'lowerLeft_Cloud_Vote',
                         'lowerRight_Cloud_Vote', 'boondingBox', 'original_filename', 'data_type', 'model_fit_type',
                         'geometric_max_err']

    # not common to all
    # LOCAL_ATTR = ['gain_state', 'scan_line_anomaly', 'sensor_mode', 'cloud_cover_automated']

    # per band
    LOCAL_ATTR_BAND = {
        'B1': ['saturation_band_1', 'saturation_pixels_band_1', 'sb_pixels_band_1', 'image_quality_band_1'],
        'B2': ['saturation_band_2', 'saturation_pixels_band_2', 'sb_pixels_band_2', 'image_quality_band_2'],
        'B3': ['saturation_band_3', 'saturation_pixels_band_3', 'sb_pixels_band_3', 'image_quality_band_3'],
        'B4': ['saturation_band_4', 'saturation_pixels_band_4', 'sb_pixels_band_4', 'image_quality_band_4'],
        'B5': ['saturation_band_5', 'saturation_pixels_band_5', 'sb_pixels_band_5', 'image_quality_band_5'],
        'B6': ['saturation_band_6', 'saturation_pixels_band_6', 'sb_pixels_band_6', 'image_quality_band_6'],
        'B6_VCID_1': ['saturation_band_6_VCID_1', 'saturation_pixels_band_6_VCID_1', 'sb_pixels_band_6_VCID_1',
                      'image_quality_band_6_VCID_1'],
        'B6_VCID_2': ['saturation_band_6_VCID_2', 'saturation_pixels_band_6_VCID_2', 'sb_pixels_band_6_VCID_2',
                      'image_quality_band_6_VCID_2'],
        'B7': ['saturation_band_7', 'saturation_pixels_band_7', 'sb_pixels_band_7', 'image_quality_band_7'],
        'B8': ['saturation_band_8', 'saturation_pixels_band_8', 'sb_pixels_band_8', 'image_quality_band_8'],
    }

    #
    # map not common to all per sat/mode
    #
    MAP_LOCAL_ATTR = {
        'L1_MSS': ['cloud_cover_automated'],
        'L2_MSS': ['cloud_cover_automated'],
        'L3_MSS': ['cloud_cover_automated'],
        'L4_MSS': ['cloud_cover_automated'],
        'L5_MSS': ['cloud_cover_automated'],

        'L4_TM': ['sensor_mode'],
        'L5_TM': ['sensor_mode', 'cloud_cover_automated'],

        'L7_ETM': ['sensor_mode', 'gain_state', 'scan_line_anomaly'],
    }

    #
    # tell which band is available per sat/mode
    #
    MAP_LOCAL_ATTR_BAND = {
        'L1_MSS': ['B4', 'B5', 'B6', 'B7'],
        'L2_MSS': ['B4', 'B5', 'B6', 'B7'],
        'L3_MSS': ['B4', 'B5', 'B6', 'B7'],

        'L4_MSS': ['B1', 'B2', 'B3', 'B4'],
        'L5_MSS': ['B1', 'B2', 'B3', 'B4'],

        'L4_TM': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
        'L5_TM': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'],

        'L7_ETM': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6_VCID_1', 'B6_VCID_2', 'B7', 'B8'],
    }

    # top folder
    METADATA_SUFFIX = 'MD.XML'  # TODO: probably there is no MD.XML, just MTR.XML
    METADATA2_SUFFIX = 'MTR.XML'
    QR_PDF__SUFFIX = 'QR.PDF'
    QR_XML__SUFFIX = 'QR.XML'
    #
    # browse can ends with BP.PNG or BI.PNG
    #
    BROWSE_SUFFIX = 'BI.PNG'
    BROWSE_SUFFIX2 = 'BP.PNG'
    SI_SUFFIX = 'SI.PNG'
    # EO folder
    MTL_SUFFIX = 'MTL.txt'

    #
    # source naming convention
    srcnamingConvention = NamingConvention.PATTERN_INSTANCE_WRS_SCENE_DDOTFV

    # from src MD.XML/MTR.XML file
    mapping_MD_MTF = {
        metadata.METADATA_FOOTPRINT: '/featureOfInterest/Footprint/multiExtentOf/MultiSurface/surfaceMember/Polygon/exterior/LinearRing/posList',
        metadata.METADATA_SCENE_CENTER: '/featureOfInterest/Footprint/centerOf/Point/pos',
        metadata.METADATA_CLOUD_COVERAGE: '/result/EarthObservationResult/cloudCoverPercentage',
        'illuminationAzimuthAngle': '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/illuminationAzimuthAngle',
        'illuminationZenithAngle': '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/illuminationZenithAngle',
        'illuminationElevationAngle': '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/illuminationElevationAngle',
        }

    # from QR.XML file
    mapping_QR = {metadata.METADATA_ACQUISITION_DATE: '/item/metadataSet/metadata@name==Processing Date',
                  metadata.METADATA_PROCESSING_TIME: '/item/metadataSet/metadata@name==Acquisition Date',
                  }

    # from MTL.txt file
    mapping_MTL = {'model': 'L1_METADATA_FILE/PRODUCT_METADATA/DATA_TYPE',
                   metadata.METADATA_PROCESSING_TYPE: 'L1_METADATA_FILE/PRODUCT_METADATA/DATA_TYPE',
                   'CLOUD_COVER_AUTOMATED_L1': 'L1_METADATA_FILE/IMAGE_ATTRIBUTES/CLOUD_COVER_AUTOMATED_L1',
                   'MODEL_FIT_TYPE': 'L1_METADATA_FILE/IMAGE_ATTRIBUTES/MODEL_FIT_TYPE',
                   'GEOMETRIC_MAX_ERR': 'L1_METADATA_FILE/IMAGE_ATTRIBUTES/GEOMETRIC_MAX_ERR',
                   }

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        self.metadata_path = None
        self.metadataSrcContent = None
        self.qr_xml_path = None
        self.qr_pdf_path = None
        self.si_path = None
        self.browse_path = None
        self.eo_path = None
        self.mtl_path = None
        #
        self.mdXmlAdapter = None

        # try to load src
        try:
            namingConventionSip = NamingConvention(self.srcnamingConvention)
            self.eoSipProduct = product_EOSIP.Product_EOSIP(path)
            self.eoSipProduct.debug = 0
            self.eoSipProduct.setNamingConventionSipInstance(namingConventionSip)
            self.eoSipProduct.setNamingConventionEoInstance(namingConventionSip)

            # metadata can be in MD.XML or MTR.XML
            # so set MD.XML alias in helper
            typeCode = os.path.basename(path)[10:20]
            print(" ##### SOURCE typeCode:%s" % typeCode)
            # if typeCode=='TM__GEO_1P' or typeCode=='MSS_GEO_1P' or typeCode=='MSS_GTC_1P' or typeCode=='ETM_GTC_1P':
            if 1 == 1:
                mtrName = os.path.basename(path).split('.')[0]
                print(" ##### mtrName:%s" % mtrName)
                eoSipHelper = eosip_product_helper.Eosip_product_helper(self.eoSipProduct)
                # set helper with MD alias
                eoSipHelper.setMdXmlAlias(mtrName + '.MTR.XML')
                # set adapter
                self.mdXmlAdapter = landsat1_7_mdAdapter.Landsat1_7_mdAdapter()
                eoSipHelper.setXmlAdapter(self.mdXmlAdapter)
                self.eoSipProduct.eoSipHelper = eoSipHelper
                print(" ##### eoSipHelper set")

            # load the EoSip, will parse the MD.XML
            #
            # the src with MTR will result in no metadata being read, and refine will throw an error
            self.eoSipProduct.loadProduct()

            #
            print("  loaded source EoSip;%s" % self.eoSipProduct.info())
            self.eoSipMetadata = metadata.Metadata()
            numAdded, helper = self.eoSipProduct.extractMetadata(self.eoSipMetadata)
            print("  number of source metadata added:%s" % numAdded)
            print("  SOURCE METADATA:%s" % self.eoSipMetadata.toString())
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" Error load source EoSip; %s %s" % (exc_type, exc_obj))
            traceback.print_exc(file=sys.stdout)
            # raise Exception("Error load source EoSip; %s %s" % (exc_type, exc_obj))
            raise e

        if self.debug != 0:
            print(" init class Product_landsat17_zip")

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
    # it is already a EoSip
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract directory product '%s' to path:%s" % (self.path, folder))

        self.workFolder = folder
        # make it unique to avoid problem if tmp folders are not empty/ were not deleted
        # too long for windows VM shared folder:
        # self.EXTRACTED_PATH = "%s/EO_part_%s" % (self.workFolder, self.origName.split('.')[0])
        # bo, loosy solution:
        self.EXTRACTED_PATH = "%s/EO_%s" % (self.workFolder, int(random.random() * 1000000000))

        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []

        if not dont_extract:
            print(" extracting EoSip inside:%s ..." % self.EXTRACTED_PATH)
            z.extractall(self.EXTRACTED_PATH)
            print("  extracting done")
        else:
            print("  dont_extract is set")

        n = 0
        for root, dirs, files in os.walk(self.EXTRACTED_PATH, topdown=False):
            for name in files:
                aPath = os.path.join(self.EXTRACTED_PATH, root, name)
                print((" check extracted file[%s]:%s" % (n, aPath)))

                n = n + 1
                if self.debug != 0:
                    print("  zip content[%d]:%s" % (n, name))
                if name.endswith(self.METADATA_SUFFIX):
                    self.metadata_path = aPath
                    if self.debug != 0:
                        print("   METADATA %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.METADATA2_SUFFIX):
                    self.metadata_path = aPath
                    if self.debug != 0:
                        print("   METADATA2 %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.QR_PDF__SUFFIX):
                    self.qr_pdf_path = aPath
                    if self.debug != 0:
                        print("   QR PDF %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.QR_XML__SUFFIX):
                    self.qr_xml_path = aPath
                    if self.debug != 0:
                        print("   QR XML %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.BROWSE_SUFFIX):
                    self.browse_path = aPath
                    if self.debug != 0:
                        print("   BROWSE %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.BROWSE_SUFFIX2):
                    self.browse_path = aPath
                    if self.debug != 0:
                        print("   BROWSE %s extracted at path:%s" % (name, folder + '/' + name))
                elif name.endswith(self.SI_SUFFIX):
                    self.si_path = aPath
                    if self.debug != 0:
                        print("   SI %s extracted at path:%s" % (name, folder + '/' + name))

                # EO folder
                elif name.endswith(self.MTL_SUFFIX):
                    self.mtl_path = aPath
                    if self.debug != 0:
                        print("   MTL %s extracted at path:%s" % (name, folder + '/' + name))
                #
                else:
                    if self.debug != 0:
                        print("   EO part %s extracted at path:%s" % (name, folder + '/' + name))

                if name.endswith('/'):
                    d = d + 1

                # relPath = aPath[len(self.EXTRACTED_PATH) + 1:]
                relPath = os.path.join(root, name)[len(self.EXTRACTED_PATH) + 1:]
                print("   content[%s] workfolder relative path:%s" % (n, relPath))
                self.contentList.append(relPath)
        # os._exit(1)

    #
    # MSS_GEO_1P
    # MSS_GTC_1P
    # TM__GEO_1P
    # TM__GTC_1P
    # ETM_GTC_1P
    #
    def buildTypeCode(self):
        return

    #
    # get L7 band gain state
    #
    def getBandGainState(self, met):
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        platform = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        if platform == '7':
            if instrument == 'ETM':
                groupDoc = GroupedDocument()
                groupDoc.loadDocument(self.mtl_path)

                # is in IMAGE_ATTRIBUTES group
                start, stop = groupDoc.getGroupByPath('L1_METADATA_FILE/PRODUCT_PARAMETERS')
                print(" @@##@@ PRODUCT_PARAMETERS group: start line:%s; stop line:%s" % (start, stop))

                platId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
                instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
                mapKey = "L%s_%s" % (platId, instrument)
                result = ''
                for bandId in self.MAP_LOCAL_ATTR_BAND[mapKey]:
                    print(" @@##@@ get band gain state for bandId:%s" % bandId)
                    # if like GAIN_BAND_1 in MTL file
                    keyName = ' GAIN_BAND_%s = "' % bandId[1:]
                    print(" @@##@@ get band gain state for bandId:%s, keyName=%s" % (bandId, keyName))
                    aValue = '?'
                    for i in range(start, stop):
                        aLine = groupDoc.getLine(i)
                        print(("  @@ look for %s info at line index:%s.Line:%s" % (keyName, i, aLine)))
                        if aLine.find(keyName) >= 0:
                            aValue = aLine.split('=')[1].strip().replace('"', '')
                            break
                    if len(result) > 0:
                        result += ' '
                    result += aValue
                print(" @@@@@@@@@@@@@@ getBandGainState result:%s" % result)
                if result.find('?') >= 0:
                    raise Exception("Some band gain state was not found:%s" % result)
                met.addLocalAttribute('gain_state', result)

    #
    # get L7 scan line anomaly ON/OFF based on date
    #
    def getScanLineAnomaly(self, met):
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        tmp = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        start = met.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        secs = formatUtils.timeFromDatePatterm(start)
        if tmp == '7':
            if instrument == 'ETM':
                secsLimit = formatUtils.timeFromDatePatterm(L7_ETM_SCAN_LINE_ANOMALY_SWITCH)
                if secs < secsLimit:
                    met.setMetadataPair('scan_line_anomaly', 'ON')
                else:
                    met.setMetadataPair('scan_line_anomaly', 'OFF')

    #
    # get L4 L5 TM and  L7 ETMsensor_mode: SAM or BUMPER based on date
    #
    def getBumperMode(self, met):
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        tmp = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        start = met.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        secs = formatUtils.timeFromDatePatterm(start)
        if tmp == '5' or tmp == '4':
            if instrument == 'TM':
                secsLimit = formatUtils.timeFromDatePatterm(L5_BUMPER_MODE_SWITCH)
                if secs < secsLimit:
                    met.setMetadataPair('sensor_mode', 'SAM')
                else:
                    met.setMetadataPair('sensor_mode', 'BUMPER')
        elif tmp == '7':
            if instrument == 'ETM':
                secsLimit = formatUtils.timeFromDatePatterm(L7_BUMPER_MODE_SWITCH)
                if secs < secsLimit:
                    met.setMetadataPair('sensor_mode', 'SAM')
                else:
                    met.setMetadataPair('sensor_mode', 'BUMPER')

    #
    # Example: LE07_L1TP_016039_20040918_20160211_KSE
    #
    def buildOriginalFilename(self, met):
        sensor = met.getMetadataValue(metadata.METADATA_INSTRUMENT)

        platId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)

        processingType = met.getMetadataValue(metadata.METADATA_PROCESSING_TYPE)  # 'L1G', 'L1Gt', 'L1T'
        if processingType == 'L1G':
            processingType = 'L1GS'
        elif processingType == 'L1Gt':
            processingType = 'L1GT'
        elif processingType == 'L1T':
            processingType = 'L1TP'
        else:
            raise Exception("invalid processingType:%s" % processingType)

        tmp = met.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED)
        path = formatUtils.normaliseNumber(tmp, 3, '0')

        tmp = met.getMetadataValue(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        row = formatUtils.normaliseNumber(tmp, 3, '0')

        tmp = met.getMetadataValue(metadata.METADATA_ACQUISITION_DATE)
        ymd = tmp.split('T')[0].replace('-', '')

        tmp = met.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        ymd2 = tmp.split('T')[0].replace('-', '')

        res = "L%s0%s_%s_%s%s_%s_%s_%s" % (sensor[0], platId, processingType, path, row, ymd, ymd2,
                                           met.getMetadataValue(metadata.METADATA_GROUND_STATION_IDENTIFIER))
        print(" original_filename=%s" % tmp)

        if not len(tmp) != len(REF_ORIGINAL_FILENAME):
            raise Exception("wrong original_filename length:%s VS %s" % (len(tmp), len(REF_ORIGINAL_FILENAME)))
        met.addLocalAttribute("original_filename", res)

    #
    # set local attribute for sat/mode
    # common are already set
    #
    def setLocalAttr(self, met):
        platId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        mapKey = "L%s_%s" % (platId, instrument)

        if not mapKey in self.MAP_LOCAL_ATTR:
            raise Exception("no mapKey '%s' in MAP_LOCAL_ATTR")

        # the not common to all
        for attrName in self.MAP_LOCAL_ATTR[mapKey]:
            print(" @@##@@ HOHOHO should set local attribute:%s" % attrName)
            if met.localAttributeExists(attrName):
                print(" @@##@@ HOHOHO local attribute:%s already present; value is:%s" % (
                attrName, met.getLocalAttributeValue(attrName)))
            else:
                value = met.getMetadataValue(attrName)
                print(" @@##@@ HOHOHO  should set local attribute:%s; value is:%s; type:%s" % (
                attrName, value, type(value)))
                if value is None:
                    met.addLocalAttribute(attrName, base_metadata.VALUE_UNKNOWN)
                else:
                    met.addLocalAttribute(attrName, value)

        # the band
        if not mapKey in self.MAP_LOCAL_ATTR_BAND:
            raise Exception("no mapKey '%s' in MAP_LOCAL_ATTR_BAND  ")

        print("\n\n ##@@## all bands:%s" % self.bands)
        print(" ##@@## bands to resolve for mapKey:%s -> %s\n\n" % (mapKey, self.MAP_LOCAL_ATTR_BAND[mapKey]))
        for bandId in self.MAP_LOCAL_ATTR_BAND[mapKey]:
            print(" @@##@@ should set local attribute for bandId:%s" % bandId)
            # bandId start at 0
            band = self.bands[bandId[1:]]

            for attrName in self.LOCAL_ATTR_BAND[bandId]:
                print(" @@##@@ should set bandId %s local attribute :%s" % (bandId, attrName))
                done = False
                if attrName.startswith('saturation_band_'):
                    met.addLocalAttribute(attrName, band.saturation)
                    done = True
                elif attrName.startswith('saturation_pixels_band_'):
                    met.addLocalAttribute(attrName, band.saturation_ratio_pm)
                    done = True
                elif attrName.startswith('sb_pixels_band_'):
                    met.addLocalAttribute(attrName, band.sb_pixels)
                    done = True
                elif attrName.startswith('image_quality_band_'):
                    met.addLocalAttribute(attrName, band.quality)
                    done = True

                if bandId == 'B6' and not done:
                    # VCID_1
                    if attrName == 'saturation_band_6_VCID_1':
                        met.addLocalAttribute(attrName, band.saturation_VCID)
                    elif attrName == 'saturation_pixels_band_6_VCID_1':
                        met.addLocalAttribute(attrName, band.pixels_VCID_ratio_pm)
                    elif attrName == 'sb_pixels_band_6_VCID_1':
                        met.addLocalAttribute(attrName, band.sb_pixels_VCID)
                    elif attrName == 'image_quality_band_6_VCID_1':
                        met.addLocalAttribute(attrName, band.quality_VCID)
                    # VCID_2
                    elif attrName == 'saturation_band_6_VCID_2':
                        met.addLocalAttribute(attrName, band.saturation_VCID_2)
                    elif attrName == 'saturation_pixels_band_6_VCID_2':
                        met.addLocalAttribute(attrName, band.pixels_VCID_2_ratio_pm)
                    elif attrName == 'sb_pixels_band_6_VCID_2':
                        met.addLocalAttribute(attrName, band.sb_pixels_VCID_2)
                    elif attrName == 'image_quality_band_6_VCID2':
                        met.addLocalAttribute(attrName, band.quality_VCID_2)
                    else:
                        raise Exception("unknown attrName:'%s'" % attrName)

    #
    # extract metadat from MTL file:
    # - create band list
    # - SB_PIXELS_BAND_X
    # - IMAGE_QUALITY_BAND_X
    #
    def extractMetadataFromMtl(self, met):
        groupDoc = GroupedDocument()
        groupDoc.loadDocument(self.mtl_path)

        num_added = 0
        for field in self.mapping_MTL:
            rule = self.mapping_MTL[field]
            if self.debug == 0:
                print(" ##### Handle MTL matadata:%s" % field)

            try:
                toks = rule.split('/')
                n = 0
                start = 0
                stop = groupDoc.getNumberOfLines()
                aValue = None
                for tok in toks:
                    if n < len(toks) - 1:
                        print(("\n we are at level[%s]:'%s'" % (n, tok)))
                        start2, stop2 = groupDoc.getGroupBetween(tok, start, stop)
                        start = start2
                        stop = stop2
                    else:
                        print(("\n we are at last level[%s]:'%s'" % (n, tok)))
                        # throws exception if not found:
                        try:
                            aValue = groupDoc.getGroupValue(tok, start, stop)
                            aValue = aValue.replace('"', '').strip()
                            print((" =====>>>>>> field:%s; value=%s" % (field, aValue)))
                            met.setMetadataPair(field, aValue)
                        except:
                            met.setMetadataPair(field, sipBuilder.VALUE_NOT_PRESENT)
                        num_added += 1
                    n += 1
            except Exception as e:
                # some field may not b epresent, like CLOUD_COVER_AUTOMATED
                print((" =====>>>>>> field:%s; ERROR:%s" % (field, e)))
                raise e

        # get band info
        self.bands = {}
        platId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        mapKey = "L%s_%s" % (platId, instrument)
        # is in IMAGE_ATTRIBUTES group
        start, stop = groupDoc.getGroupByPath('L1_METADATA_FILE/IMAGE_ATTRIBUTES')
        print(" @@##@@ MTL IMAGE_ATTRIBUTES group: start line:%s; stop line:%s" % (start, stop))
        # os._exit(1)
        for bandId in self.MAP_LOCAL_ATTR_BAND[mapKey]:
            print(" @@##@@ MTL should get info for bandId:%s" % bandId)  # is like 'B1'
            band = bandId[1:]
            aBand = Band(bandId)
            for i in range(start, stop):
                print(("  @@ look for band %s info at line index:%s" % (band, i)))
                aLine = groupDoc.getLine(i)
                print(("  @@ look for band %s info at line:%s" % (band, aLine)))
                # sb_pixels_
                if aLine.find('SB_PIXELS_BAND_%s' % band) >= 0:
                    aValue = aLine.split('=')[1].strip()
                    print(("   band %s SB_PIXELS_BAND:%s" % (band, aValue)))
                    aBand.sb_pixels = aValue
                elif aLine.find('IMAGE_QUALITY_BAND_%s' % band) >= 0:
                    aValue = aLine.split('=')[1].strip()
                    print(("   band %s IMAGE_QUALITY_BAND_:%s" % (band, aValue)))
                    aBand.quality = aValue

            self.bands[band] = aBand
            print(" @@##@@ MTL band added in map with key:%s" % band)  # is like '1'

    #
    # extract metadata from QR.XML file
    # - "Acquisition Date" + "Processing Date"
    # - call getBandInfo
    #
    def extractMetadataFromQr(self, met):
        fd = open(self.qr_xml_path, 'r')
        self.metadataQrContent = fd.read()
        fd.close()

        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metadataQrContent)
        helper.parseData()

        #
        # get fields
        # resultList = []
        # op_element = helper.getRootNode()
        num_added = 0

        # singleNode = False
        n = 0
        for field in self.mapping_QR:
            if self.mapping_QR[field].find("@") >= 0:
                attrNameValue = self.mapping_QR[field].split('@')[1]
                path = self.mapping_QR[field].split('@')[0]
                attrName = attrNameValue.split('==')[0]
                attrValue = attrNameValue.split('==')[1]
                print(" @@##@@ QR: look for node[%s]; path=%s; attrName=%s; attrValue=%s" % (
                n, path, attrName, attrValue))
                aList = helper.getNodeContentPathAttrFiltered(path, attrName, attrValue)
                print("  found %s nodes" % len(aList))
                if len(aList) == 1:
                    aValue = helper.getNodeText(aList[0])
                    met.setMetadataPair(field, aValue)
                    num_added += 1
                    if 1 == 1 or self.debug != 0:
                        print("  num_added[%s] 1 -->%s=%s" % (num_added, field, aValue))
                else:
                    raise Exception("getNodeContentPathAttrFiltered return wrong number of node:%s" % len(aList))
            else:
                attrNameValue = None
                path = self.mapping_QR[field]

            n += 1

        #
        self.getBandInfo(helper, met)

    #
    # get some band info from QR file:
    # - has already the xmlHelper
    # - saturation_pixel_X
    #
    # inside /inspection/inspection...
    #
    def getBandInfo(self, helper, met):
        #
        aNode = helper.getFirstNodeByPath(None, '/inspection', None)
        if aNode is None:
            raise Exception("no inspection node found in QR")

        aList = None
        typecode = met.getMetadataValue(metadata.METADATA_TYPECODE)

        # the node attribute differ...:
        aList = helper.getNodeContentPathAttrFiltered('/inspection/inspection', 'id', 'level1ImageStandardPlan')
        if len(aList) == 0:
            aList = helper.getNodeContentPathAttrFiltered('/inspection/inspection', 'id', 'level1ImagePlan')
        print(" getBandInfo; found %s bands" % len(aList))

        n = 0
        for aNode in aList:
            # band identification in 'item' attribute
            # like: LM12010391976144ESA00_B4.TIF_LM12010391976144ESA00
            # or  : LE71820392001120ESA00_B6_VCID_1.TIF_LE71820392001120ESA00
            bandItem = helper.getNodeAttributeText(aNode, 'item')
            print("@@##@@##@@## this is band item:%s" % bandItem)

            bandId = bandItem.split('.')[0].split('_')
            if len(bandId) == 4:
                bandId = '_'.join(bandId[1:])[1:]
            else:
                bandId = bandId[1][1]
            print("@@##@@##@@## this is band id:%s" % bandId)

            path = '/inspection/message/para/para/table/tgroup/tbody'
            node1 = helper.getFirstNodeByPath(aNode, path, None)
            print("  band[%s]; node1=%s" % (n, node1))

            # aBand = None
            # try:
            #    aBand = self.bands[bandId]
            # except:
            #    print "  Error getting band '%s' from map; bands in map:%s" % (bandId, self.bands)
            #    os._exit(1)

            if bandId in self.bands:
                aBand = self.bands[bandId]
                # look for row with entry=='High saturation count'
                aList2 = []
                helper.getNodeByPath(node1, '/row', None, aList2)
                print("  band[%s]; num of rows node:%s" % (n, len(aList2)))
                nrow = 0
                toGet = False
                for item in aList2:
                    #
                    aList3 = helper.getNodeChildrenByName(item, 'entry')
                    oldV = None
                    nEntry = 0
                    for row in aList3:
                        v = None
                        try:
                            v = str(helper.getNodeText(row))
                        except:
                            v = "NON ASCII !!"

                        if toGet:
                            if oldV == 'High saturation count':
                                # valuie like 1234 samples
                                print("  set band[%s] saturation count to:%s" % (n, v))
                                aBand.saturation_pixels = v.split(' ')[0]
                                aBand.saturation = 'Y'
                            elif oldV == 'Non-background samples':
                                # valuie like 1234 samples
                                print("  set band[%s] pixels count to:%s" % (n, v))
                                aBand.pixels = v.split(' ')[0]
                            toGet = False
                            oldV = None

                        if v == 'High saturation count':
                            oldV = v
                            toGet = True
                        elif v == 'Non-background samples':
                            oldV = v
                            toGet = True

                        print("  band[%s]; row[%s]; entry[%s]=%s" % (n, nrow, nEntry, v))
                        nEntry += 1
                    nrow += 1

                # set ratio in band
                if aBand.pixels != -1 and aBand.saturation_pixels != -1:
                    aBand.saturation_ratio_pm = (float(aBand.saturation_pixels) / float(aBand.pixels)) * 1000
                # get sb_pixel for non TM and ETM+
                if met.getMetadataValue(metadata.METADATA_SENSOR_NAME) == 'MSS':
                    raise Exception("MSS band sb_pixel extraction to be done!")

                # self.bands[aBand.id] = aBand

                print(" ###@@@### aBand[%s]: %s" % (n, aBand.info()))
                n += 1

            else:
                print(" ###@@@### WARNING: QR has info about band not in map:%s" % bandId)
                os._exit(1)

        # do we have enought band?
        print("##@@##@@## found bands:%s" % self.bands)
        platId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        instrument = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        mapKey = "L%s_%s" % (platId, instrument)

        if not mapKey in self.MAP_LOCAL_ATTR:
            raise Exception("no mapKey '%s' in MAP_LOCAL_ATTR")
        # the band
        if not mapKey in self.MAP_LOCAL_ATTR_BAND:
            raise Exception("no mapKey '%s' in MAP_LOCAL_ATTR_BAND  ")
        if len(self.MAP_LOCAL_ATTR_BAND[mapKey]) != len(self.bands):
            raise Exception("number of band mismatch for mapKey '%s': should be:%s but got:%s" % (
            mapKey, len(self.MAP_LOCAL_ATTR_BAND[mapKey]), len(self.bands)))

        # os._exit(1)

    #
    # entry point of metadata extraction, do in order:
    # - this one get info from MD.XML or MTL.XML
    # - from the QR file
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1

        # merge src eosip medata with self
        met.merge(self.eoSipMetadata)

        # use what contains the metadata file
        if self.metadata_path is None:
            raise Exception("no metadata to be parsed")

        #
        # extract additional metadata (from base EoSip) from MD.XML
        # new: of use the eoSipHelper.adapter in case of MTR.XML
        #
        if self.mdXmlAdapter is None:
            print(" extract additional metadata from MD.XML")
            fd = open(self.metadata_path, 'r')
            self.metadataSrcContent = fd.read()
            fd.close()
        else:
            print(" extract additional metadata from mdAdapter")
            self.metadataSrcContent = self.mdXmlAdapter.getMetadataXml()

        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metadataSrcContent)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.mapping_MD_MTF:
            if self.mapping_MD_MTF[field].find("@") >= 0:
                attr = self.mapping_MD_MTF[field].split('@')[1]
                path = self.mapping_MD_MTF[field].split('@')[0]
            else:
                attr = None
                path = self.mapping_MD_MTF[field]

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

        # get version from SRC filename
        toks1 = self.origName.split('_')
        toks2 = SRC_REF_NAME.split('_')
        # print(" toks1 length:%s" % len(toks1))
        if len(toks1) != len(toks2):
            raise Exception(
                'Source product has incorrect name, bad token length; %s VS ref:%s' % (len(toks1), len(toks2)))
        tmp = toks1[-1].split('.')[0]
        print(("  @@@@@@@@@@@@@@@@@@ version from source file:'%s'" % tmp))
        met.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, tmp)

        # extract from MTL file (present in all TDS product I have):
        if self.mtl_path is not None:
            print(" MTL file")
            self.extractMetadataFromMtl(met)
        else:
            raise Exception(" NO MTL file")

        # extract from QR file (NOT present in all TDS product I have):
        if self.qr_xml_path is not None:
            print(" QR file")
            self.extractMetadataFromQr(met)
        else:
            raise Exception(" NO QR file")
        # met.setMetadataPair(metadata.METADATA_ACQUISITION_DATE, '20000101')
        # met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, '19000101')

        # codespaces base on platform ID
        tmp = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        if int(tmp) >= 1 and int(tmp) <= 3:
            met.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED,
                                'urn:esa:eop:Landsat:WRS1:frames')
            met.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED,
                                'urn:esa:eop:Landsat:WRS1:relativeOrbits')
        elif int(tmp) > 3 and int(tmp) <= 7:
            met.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED,
                                'urn:esa:eop:Landsat:WRS2:frames')
            met.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED,
                                'urn:esa:eop:Landsat:WRS2:relativeOrbits')
        else:
            raise Exception("invalid platformId:'%s'" % tmp)

        # file class:
        met.setMetadataPair(metadata.METADATA_FILECLASS, self.origName[5:9])

        # type code:
        typecode = self.origName[10:20]
        if not typecode in REF_TYPECODE:
            raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
        met.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        #
        # local attributes
        #

        # get the original one
        doc = helper.getDomDoc()
        earthObservationMetaDataNodes = doc.getElementsByTagName('eop:EarthObservationMetaData')
        vendorSpecificNodes = earthObservationMetaDataNodes[0].getElementsByTagName('eop:vendorSpecific')
        print(" number of src vendorSpecific nodes:%s" % len(vendorSpecificNodes))
        n = 0
        for aNode in vendorSpecificNodes:
            attrName = aNode.getElementsByTagName('eop:localAttribute')
            attrValue = aNode.getElementsByTagName('eop:localValue')
            aName = helper.getNodeText(attrName[0])
            aValue = helper.getNodeText(attrValue[0])
            print("  src vendorSpecific[%s]; %s=%s" % (n, aName, aValue))
            # Cloud_Vote range is 0-9 in spec 2.1. 0-10 in V1 EoSip. use 9 where value is 10
            if aName.endswith("Cloud_Vote"):
                if int(aValue) == 10:
                    print(" %%%%@@@@%%%% src vendorSpecific %s change from %s to 9" % (aName, aValue))
                    aValue = "9"
            met.addLocalAttribute(aName, aValue)
            n += 1

        # extract illuminationAzimuthAngle, illuminationZenithAngle, illuminationElevationAngle
        aList = doc.getElementsByTagName('eop:illuminationAzimuthAngle')
        if len(aList) == 1:
            met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, helper.getNodeText(aList[0]))
        else:
            raise Exception("no eop:illuminationAzimuthAngle found in MD.XML")
        #
        aList = doc.getElementsByTagName('eop:illuminationZenithAngle')
        if len(aList) == 1:
            met.setMetadataPair(metadata.METADATA_SUN_ZENITH, helper.getNodeText(aList[0]))
        else:
            raise Exception("no eop:illuminationZenithAngle found in MD.XML")
        #
        aList = doc.getElementsByTagName('eop:illuminationElevationAngle')
        if len(aList) == 1:
            met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, helper.getNodeText(aList[0]))
        else:
            raise Exception("no eop:illuminationElevationAngle found in MD.XML")

        # bounding box
        aFootprint = met.getMetadataValue(metadata.METADATA_FOOTPRINT)
        browseIm = BrowseImage()
        browseIm.setFootprint(aFootprint)
        browseIm.calculateBoondingBox()

        # MTR.XML have no scene centre
        if self.mdXmlAdapter is not None:
            browseIm.calculateCenter()
            lat, lon = browseIm.getCenter()
            met.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lat, lon))

        #
        met.addLocalAttribute("boundingBox", browseIm.getBoundingBox())

        # data_type: L1G, L1Gt, L1T . 'MSS_GEO_1P', 'MSS_GTC_1P', 'TM__GEO_1P', 'TM__GTC_1P', 'ETM_GTC_1P'}
        # is equal to  processing type
        tmp = met.getMetadataValue(metadata.METADATA_PROCESSING_TYPE)
        if tmp in REF_PROCESSING_TYPE:
            met.addLocalAttribute("data_type", tmp)
        else:
            raise Exception("Wrong data_type:%s" % tmp)

        """if 1==2:
            if tmp == 'MSS_GEO_1P':
                met.addLocalAttribute("data_type", 'L1g')
            elif tmp == 'TM__GEO_1P':
                met.addLocalAttribute("data_type", 'L1g')
            elif tmp == 'MSS_GTC_1P':
                met.addLocalAttribute("data_type", 'L1Gt')
            elif tmp == 'TM__GTC_1P':
                met.addLocalAttribute("data_type", 'L1Gt')
            elif tmp == 'ETM_GTC_1P':
                met.addLocalAttribute("data_type", 'L1T')
            else:
                raise Exception("invalid typecode:%s" % tmp)"""

        # model_fit_type
        met.addLocalAttribute("model_fit_type", "%s_X_X" % tmp)

        # geometric_max_err
        met.addLocalAttribute("geometric_max_err", metadata.VALUE_UNKNOWN)

        # get station from fileclass
        tmp = met.getMetadataValue(metadata.METADATA_FILECLASS)
        met.setMetadataPair(metadata.METADATA_GROUND_STATION_IDENTIFIER, tmp[1:])

        #
        self.buildOriginalFilename(met)

        # set the 'sensor_mode' for L4 L5 and L7 TM ETM+
        self.getBumperMode(met)

        # set L7 ETM scan line anomaly ON/OFF based on date
        self.getScanLineAnomaly(met)

        # get L7 ETM band gain state
        self.getBandGainState(met)

        #
        self.metadata = met

        return num_added

    #
    # refine the metada
    #
    def refineMetadata(self):
        #
        self.metadata.setMetadataPair(metadata.METADATA_BROWSES_TYPE, 'QUICKLOOK')
        #
        self.buildTypeCode()

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


#
# represent landsat bands
#
class Band:

    def __init__(self, id):
        self.id = id
        self.saturation = '?'
        self.pixels = -1
        self.saturation_pixels = -1
        self.saturation_ratio_pm = -1  # per mille
        self.sb_pixels = 'Not applicable'
        self.quality = 'Not applicable'
        # for band == 6
        self.pixels_VCID = -1
        self.pixels_VCID_ratio_pm = -1.0
        self.saturation_VCID = '?'
        self.sb_pixels_VCID = 'Not applicable'
        self.quality_VCID = 'Not applicable'
        self.pixels_VCID_2 = -1
        self.saturation_VCID_2 = '?'
        self.sb_pixels_VCID_2 = 'Not applicable'
        self.quality_VCID_2 = 'Not applicable'

    def info(self):
        return "band id:%s\n saturation=%s\n pixels=%s\n saturation_pixels=%s\n saturation per/mille:%s\n sb_pixels=%s\n quality=%s" % (
        self.id, self.saturation, self.pixels, self.saturation_pixels, self.saturation_ratio_pm, self.sb_pixels,
        self.quality)
