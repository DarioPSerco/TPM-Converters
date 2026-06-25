# -*- coding: cp1252 -*-
#
# this class represent a alos ice polar product
#
#  - 
#  - 
#
#
import os
import zipfile

#
import eoSip_converter.xmlHelper as xmlHelper
from . import metadata
# from product import Product
from .product_directory import Product_Directory
# from definitions_EoSip import sipBuilder
# from browseImage import BrowseImage
from .sectionIndentedDocument import SectionDocument

# import browse_metadata
# import formatUtils
# import geomHelper


# for verification
THE_TYPECODE = 'PSR_WB1_15'


#
#
#
class Product_Alos_Ice_Polar(Product_Directory):
    # Name of the DeliverySlip.xml file within the source product directory.
    METADATA_DELIVERY_NAME = 'DeliverySlip.xml'

    # Name of the DeliverySlip.xml file within the source product directory.
    METADATA_WORKREPORT_NAME = 'workreport'
    #
    IMAGE_PREFIX = 'IMG-'

    # XML mapping for the DeliverySlip.xml file.
    mapping_DELIVERY = {metadata.METADATA_START_DATE: 'product/start-date-time',
                        metadata.METADATA_STOP_DATE: 'product/stop-date-time',
                        metadata.METADATA_PRODUCT_SIZE: 'product/product-size',
                        metadata.METADATA_SENSOR_NAME: 'product/instrument',
                        'custom-SCENE_ID': 'product/scene-id'  # like: PSRS149505150
                        }

    # XML mapping for the workreport file.
    mapping_REPORT = {
        metadata.METADATA_SCENE_CENTER: 'Pds_PixelSpacing*|4,5',
        metadata.METADATA_FOOTPRINT: 'Pds_PixelSpacing*|6,7,10,11,12,13,8,9,6,7',
        metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Pds_UTM_ZoneNo*|0'
    }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        self.debug = 1
        self.image_path = None
        print(" init class Product_Alos_Special")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # self.logger.info(" buildEoNames")
        processInfo.addLog(" buildEoNames")
        processInfo.destProduct.buildEoNames(namingConvention)

    #
    # read metadata file
    #
    def getMetadataInfo(self):
        pass

    #
    # extract the worldview
    #
    def extractToPath(self, folder=None, dont_extract=False):
        global METADATA_DELIVERY_NAME, METADATA_WORKREPORT_NAME

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exist: %s" % folder)
        if self.debug != 0:
            print(" Extracting directory product '%s' to path: %s" % (self.path, folder))

        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []
        n = 0
        d = 0
        for name in z.namelist():
            n = n + 1
            if self.debug != 0:
                print("  Zip content[%d]: %s" % (n, name))
            if name.find(self.METADATA_DELIVERY_NAME) >= 0:
                self.metadata_delivery_path = "%s/%s" % (folder, name)
            elif name.find(self.METADATA_WORKREPORT_NAME) >= 0:
                self.metadata_workreport_path = "%s/%s" % (folder, name)
            elif name.find('/' + self.IMAGE_PREFIX) >= 0:
                self.image_path = "%s/%s" % (folder, name)

            if self.debug != 0:
                print("   %s extracted at path: %s" % (name, folder + '/' + name))
            if name.endswith('/'):
                self.tempProductDirectory = name
                d = d + 1
            self.contentList.append(name)

        # if dont_extract!=True:
        #    z.extractall(folder)

        # has only one folder
        if d == 1:
            if dont_extract != True:
                z.extractall(folder)
            if self.metadata_delivery_path != None:
                fd = open(self.metadata_delivery_path, 'r')
                self.metadata_delivery_data = fd.read()
                fd.close()

            if self.metadata_workreport_path != None:
                fd = open(self.metadata_workreport_path, 'r')
                self.metadata_workreport_data = fd.read()
                fd.close()

            self.EXTRACTED_PATH = folder

        z.close()
        fh.close()

    #
    # just one typecode
    #
    def buildTypeCode(self):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, THE_TYPECODE)

        # if not typecode in  REF_TYPECODE:
        #    raise Exception("buildTypeCode; unknown typecode:%s" % typecode)

    #
    #   Extracts the metadata of the product.
    #
    def extractMetadata(self, met=None):

        if met == None:
            raise Exception("Metadata is None")

        self.metadata = self.extractMetadata01(met)
        self.metadata = self.extractMetadata02(self.metadata)

        return

    #
    #   Extracts the first set of metadata.
    #   The extraction is performed on the 'DeliverySlip.xml' file, an XML file.
    #
    def extractMetadata01(self, met=None):

        # Extract metadata.
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)

        if self.debug != 0:
            print("metadata:%s" % self.metadata_delivery_data)
        helper.setData(self.metadata_delivery_data)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.mapping_DELIVERY:
            print("metadata extract field:%s" % field)
            if self.mapping_DELIVERY[field].find("@") >= 0:
                attr = self.mapping_DELIVERY[field].split('@')[1]
                path = self.mapping_DELIVERY[field].split('@')[0]
            else:
                attr = None
                path = self.mapping_DELIVERY[field]

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

        return met

    #
    #   Extracts the first set of metadata.
    #   The extraction is performed on the 'workreport' file, a plain-text (similar to properties) file.
    #
    def extractMetadata02(self, met=None):

        sectionDoc = SectionDocument()
        sectionDoc.setContent(self.metadata_workreport_data)
        sectionDoc.debug = 1

        # get fields
        num_added = 0

        for field in self.mapping_REPORT:
            rule = self.mapping_REPORT[field]
            aValue = None
            if self.debug == 0:
                print(" ##### Handle report matadata:%s" % field)

            toks = rule.split('|')
            if len(toks) != 2:
                raise Exception("Malformed report matadata rule:%s" % field)
            # wildcard used?
            if toks[0][-1] == '*':
                line = sectionDoc.getSectionLine(toks[0])
                # line offset(s) list are in second token
                offsets = toks[1].split(',')
                aValue = ''
                for offset in offsets:
                    nLine = line + int(offset)
                    if len(aValue) > 0:
                        aValue = "%s " % aValue
                    aValue = "%s%s" % (aValue, sectionDoc.getLineValue(nLine, None, separator='=').replace('"', ''))
                if self.debug == 0:
                    print("  report matadata:%s='%s'" % (field, aValue))
            else:
                aValue = sectionDoc.getValue(toks[0], toks[1])
            # supress initial space is any
            if aValue[0] == ' ':
                aValue = aValue[1:]
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        self.metadata = met

        return met

    #
    # Refine the metadata.
    #
    def refineMetadata(self):

        # Defining METADATA_START_DATE, METADATA_START_TIME.
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        start_tokens = start.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start_tokens[1][0:-1])

        # Defining METADATA_STOP_DATE, METADATA_STOP_TIME.
        stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)
        stop_tokens = stop.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop_tokens[1][0:-1])

        # Defining METADATA_ORBIT. # "custom-SCENE_ID" like: PSRS149505150
        sceneid = stop = self.metadata.getMetadataValue("custom-SCENE_ID")
        orbit = sceneid[4:-4]
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, orbit)

        # Defining METADATA_WRS_LONGITUDE_GRID_NORMALISED, METADATA_TRACK.
        track = str((((int(orbit) - 640) * 46) % 671) + 1)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, track)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, track)

        # Defining METADATA_WRS_LATITUDE_GRID_NORMALISED, METADATA_FRAME.
        frame = sceneid[-4:]
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, frame)
        self.metadata.setMetadataPair(metadata.METADATA_FRAME, frame)

        # Defining METADATA_INSTRUMENT, METADATA_SENSOR_OPERATIONAL_MODE.
        sensor = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, sensor)
        #
        self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
                                      'urn:esa:eop:ALOS:PALSAR:operationalMode')
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'WB1')

        # utm zone
        tmp = self.metadata.getMetadataValue(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER)
        self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, "WSG 84 / UTM zone %s" % tmp)

        # Defining METADATA_TYPECODE.
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
