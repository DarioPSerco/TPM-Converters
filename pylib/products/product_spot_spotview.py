# -*- coding: cp1252 -*-
#
# this class represent a Dimap Spot product spotView (ZIP directory product)
#
#
#
import os
import sys
import traceback
import zipfile

from . import browse_metadata
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .product_directory import Product_Directory

# import eoSip_converter.geomHelper as geomHelper
# from definitions_EoSip import sipBuilder


REF_TYPECODE = {
    'HRV__P__1A', 'HRV__P__1B', 'HRV__P__2A', 'HRV__P___3', 'HRV__X__1A',
    'HRV__X__1B', 'HRV__X__2A', 'HRV__X___3 ', 'HRI__M__1A', 'HRI__M__1B',
    'HRI__M__2A', 'HRI__M___3 ', 'HRI__X__1A', 'HRI__X__2A', 'HRI__X___3 ',
    'HRI__I__1A', 'HRI__I__1B', 'HRI__I__2', 'HRI__I___3 ', 'HRG__A__1A',
    'HRG__A__1B', 'HRG__A__2A', 'HRG__B__2A', 'HRG__A___3 ', 'HRG__J__1A',
    'HRG__J__1B', 'HRG__J__2A', 'HRG__J___3 ', 'HRG__PS_1A ', 'HRG__PS_1B ',
    'HRG__PS_2A ', 'HRG__PS__3 '
}

SPECTRAL_PROCESSING = [
    'XS', 'X', 'HX', 'I', 'J',
    'T', 'M+X', 'M+I', 'HM+X', 'HM+J',
    'T+X', 'T+J', 'P+X', 'P',
    'HM', 'M', 'S', 'Other'
]


class Product_Spot_Spotview(Product_Directory):
    PREVIEW_NAME = 'PREVIEW.JPG'
    IMAGERY_NAME = 'IMAGERY.TIF'
    METADATA_NAME = 'METADATA.DIM'
    EXTRACTED_PATH = None
    preview_data = None
    metadata_data = None
    preview_path = None
    metadata_path = None
    imagery_path = None

    xmlMapping = {metadata.METADATA_PROFILE: 'Metadata_Id/METADATA_PROFILE',
                  metadata.METADATA_START_DATE: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_DATE',
                  metadata.METADATA_START_TIME: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_TIME',
                  # metadata.METADATA_PARENT_IDENTIFIER:'Dataset_Sources/Source_Information/SOURCE_ID',
                  'SOURCE_ID': 'Dataset_Sources/Source_Information/SOURCE_ID',
                  metadata.METADATA_PROCESSING_TIME: 'Production/DATASET_PRODUCTION_DATE',
                  metadata.METADATA_PROCESSING_CENTER: 'Production/DATASET_PRODUCER_NAME',
                  metadata.METADATA_SOFTWARE_NAME: 'Production/Production_Facility/SOFTWARE_NAME',
                  metadata.METADATA_SOFTWARE_VERSION: 'Production/Production_Facility/SOFTWARE_VERSION',
                  metadata.METADATA_DATASET_NAME: 'Dataset_Id/DATASET_NAME',
                  # metadata.METADATA_ORBIT:'Dataset_Sources/Source_Information/Scene_Source/Imaging_Parameters/REVOLUTION_NUMBER',
                  metadata.METADATA_PARENT_PRODUCT: 'Dataset_Sources/Source_Information/SOURCE_ID',
                  metadata.METADATA_PLATFORM: 'Dataset_Sources/Source_Information/Scene_Source/MISSION',
                  metadata.METADATA_RESOLUTION: 'Dataset_Sources/Source_Information/Scene_Source/THEORETICAL_RESOLUTION',
                  metadata.METADATA_PLATFORM_ID: 'Dataset_Sources/Source_Information/Scene_Source/MISSION_INDEX',
                  # metadata.METADATA_PROCESSING_LEVEL:'Dataset_Sources/Source_Information/Scene_Source/SCENE_PROCESSING_LEVEL',
                  metadata.METADATA_INSTRUMENT: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                  metadata.METADATA_INSTRUMENT_ID: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT_INDEX',
                  metadata.METADATA_SENSOR_NAME: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                  # metadata.METADATA_SENSOR_CODE:'Dataset_Sources/Source_Information/Scene_Source/IMAGING_MODE',
                  'GEOMETRIC_PROCESSING': 'Data_Processing/GEOMETRIC_PROCESSING',
                  metadata.METADATA_SENSOR_CODE: 'Data_Processing/SPECTRAL_PROCESSING',
                  metadata.METADATA_DATA_FILE_PATH: 'Data_Access/Data_File/DATA_FILE_PATH@href',
                  metadata.METADATA_DATASET_PRODUCTION_DATE: 'Production/DATASET_PRODUCTION_DATE',

                  # metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE:'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
                  metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',

                  metadata.METADATA_VIEWING_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE',
                  metadata.METADATA_SUN_AZIMUTH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_AZIMUTH',
                  metadata.METADATA_SUN_ELEVATION: 'Dataset_Sources/Source_Information/Scene_Source/SUN_ELEVATION',
                  metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Coordinate_Reference_System/Horizontal_CS/HORIZONTAL_CS_CODE',
                  metadata.METADATA_SCENE_CENTER_LON: 'Dataset_Frame/Scene_Center/FRAME_LON',
                  metadata.METADATA_SCENE_CENTER_LAT: 'Dataset_Frame/Scene_Center/FRAME_LAT'
                  }

    #
    #
    #
    def __init__(self, path):
        Product_Directory.__init__(self, path)
        print(" init class Product_Dimap_Spot_Spotview")

    #
    #
    #
    def getMetadataInfo(self):
        return self.metadata_data

    #
    # extract the source product in workfolder.
    # keep the metadata file content
    # dont_extract parameter can be used to not do the extract: to correct a faulty product then re package it in EoSip 
    #
    def extractToPath(self, folder=None, dont_extract=False):
        global METADATA_NAME, PREVIEW_NAME, IMAGERY_NAME
        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract product to path:%s" % folder)
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
            if name.find(self.PREVIEW_NAME) >= 0:
                self.preview_path = "%s/%s" % (folder, name)
            elif name.find(self.METADATA_NAME) >= 0:
                self.metadata_path = "%s/%s" % (folder, name)
            elif name.find(self.IMAGERY_NAME) >= 0:
                self.imagery_path = "%s/%s" % (folder, name)

            if self.debug != 0:
                print("   %s extracted at path:%s" % (name, folder + '/' + name))
            if name.endswith('/'):
                d = d + 1
            self.contentList.append(name)

        # ESA SPOT products only have one scene in one folder
        # if d==1:
        if dont_extract != True:
            z.extractall(folder)
        if self.metadata_path != None:
            fd = open(self.metadata_path, 'r')
            self.metadata_data = fd.read()
            fd.close()

        if self.preview_path != None:
            fd = open(self.preview_path, 'r')
            self.preview_data = fd.read()
            fd.close()
        self.EXTRACTED_PATH = folder
        if self.debug != 0:
            print(" ################### self.preview_path:%s" % self.preview_path)
            # else:
        #    raise Exception("More than 1 directory in product:%d" % d)
        z.close()
        fh.close()

    #
    #
    #
    def buildTypeCode(self):
        sensor = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        sensorCode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE)
        # sensorCode=sensorCode.replace('+','')

        processLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if processLevel == '3':
            processLevel = "_%s" % processLevel
        if sensor is None or sensorCode is None or processLevel is None:
            raise Exception("can not construct typecode: some field is None")
        if sensor == 'HRVIR':
            sensor = 'HRI'

        # not sure:
        if 1 == 2:
            if sensorCode not in SPECTRAL_PROCESSING:
                raise Exception("Unknown spectral processing:'%s'" % sensorCode)

            if sensorCode == 'HM+X' and processLevel == '1A':
                sensorCode = 'A'
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_CODE, sensorCode)
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'X')
            elif sensorCode == 'XS' and processLevel == '1A':
                sensorCode = 'X'
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_CODE, sensorCode)
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'X')
            else:
                pass

        typecode = None
        if len(sensorCode) == 1:
            typecode = "%s__%s__%s" % (sensor, sensorCode, processLevel)
        elif len(sensorCode) == 2:
            typecode = "%s__%s_%s" % (sensor, sensorCode, processLevel)
        elif len(sensorCode) == 3:
            typecode = "%s_%s_%s" % (sensor, sensorCode, processLevel)
        else:
            typecode = "%s_%s_%s" % (sensor, sensorCode[0, 3], processLevel)
            # raise Exception("can not construct typecode; invalid sensorCode field length:'%s'" % sensorCode)

        # STRICTLY_COMPLY_TO_SPEC flag used?
        strict = True
        aFlag = self.metadata.getMetadataValue('STRICTLY_COMPLY_TO_SPEC')
        print(("STRICTLY_COMPLY_TO_SPEC:%s" % aFlag))
        if self.metadata.valueExists(aFlag) and aFlag == 'False':
            strict = False

        if not typecode in REF_TYPECODE:
            if strict:
                print((" #### typecode unknown: '%s'\n" % typecode))
                raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
            else:
                print((
                            " #### typecode unknown: '%s'; but STRICTLY_COMPLY_TO_SPEC is False and so we accept it\n" % typecode))

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        self.processInfo.addInfo(metadata.METADATA_SENSOR_CODE,
                                 self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE))
        self.processInfo.addInfo(metadata.METADATA_INSTRUMENT_ID,
                                 self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ID))
        self.processInfo.addInfo(metadata.METADATA_SENSOR_NAME,
                                 self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME))
        self.processInfo.addInfo(metadata.METADATA_TYPECODE, self.metadata.getMetadataValue(metadata.METADATA_TYPECODE))
        self.processInfo.addInfo(metadata.METADATA_PROCESSING_LEVEL,
                                 self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL))

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        metContent = self.getMetadataInfo()

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

        self.metadata = met

        self.extractQuality(helper, met)

        self.extractFootprint(helper, met)

        # extract 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE' which is only in SPOT5, set it in acrossTrackIncidenceAngle 
        tmpNodes = []
        helper.getNodeByPath(None, 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE', None, tmpNodes)
        if len(tmpNodes) == 1:
            tmp = helper.getNodeText(tmpNodes[0])
            print("  VIEWING_ANGLE=%s" % tmp)
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE, tmp)
        else:
            print("  no VIEWING_ANGLE")

        return num_added

    #
    # refine the metada, should perform in order:
    # - normalise date and time
    # - set platform info
    # - build type code
    #
    def refineMetadata(self):
        # check profile
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROFILE)
        print(("## profile: %s" % tmp))
        if tmp != 'SPOTView':
            raise Exception("not a SPOTView profile but:'%s'" % tmp)

        # handle METADATA_SENSOR_CODE
        if 1 == 1:
            sensorCode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE)
            if sensorCode.find('+') > 0:
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_CODE, sensorCode.replace('+', ''))

        # processing level
        tmp = self.metadata.getMetadataValue('GEOMETRIC_PROCESSING')
        if tmp != 'ORTHO':
            raise Exception("not ORTHO")
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, '2A')

        # processing time: suppress microsec
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos + 4]
        # may be only date
        if len(tmp) == 10:
            tmp += 'T00:00:00.000'

        pos = tmp.find('Z')
        if pos < 0:
            tmp = tmp + "Z"
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        # convert sun azimut from EEE format
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_AZIMUTH)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_ELEVATION)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_ELEVATION, formatUtils.EEEtoNumber(tmp))

        # tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
        # if tmp!=None:
        #    self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE)
        if tmp != metadata.VALUE_NOT_PRESENT:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE,
                                          formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE)
        if tmp != metadata.VALUE_NOT_PRESENT:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE,
                                          formatUtils.EEEtoNumber(tmp))

        # fix production date: from 2008-10-01T14:52:01.000000 to 2008-10-01T14:52:01Z
        tmp = self.metadata.getMetadataValue(metadata.METADATA_DATASET_PRODUCTION_DATE)
        pos = tmp.find('.')
        if pos > 0:
            tmp = "%sZ" % tmp[0:pos]
        self.metadata.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, tmp)

        # set scene center coordinate
        # PROBABLT is not in SPOTSCENE format
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LON)
        if tmp != None:
            tmp = formatUtils.EEEtoNumber(tmp)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, tmp)
            tmp1 = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LAT)
            tmp1 = formatUtils.EEEtoNumber(tmp1)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, tmp1)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (tmp1, tmp))
        # else:
        #    tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER

        # set scene center time, from the only we have: start time
        tmp = "%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_START_DATE),
                          self.metadata.getMetadataValue(metadata.METADATA_START_TIME))
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_TIME, tmp)
        # new:
        start = formatUtils.datePlusMsec(tmp, -4512)
        stop = formatUtils.datePlusMsec(tmp, 4512)
        # set metadata, keep 2 decimal after second
        toks = start.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, toks[1][0:-1])
        toks = stop.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, toks[1][0:-1])

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # verify that the WRS grid is ok: vs the scene id
        # BUT there is also this info in the parent identifier: Dataset_Sources/Source_Information/SOURCE_ID like: 10223228810091145361X
        # SPOT has GRS (K, J) pair. J is lat. K is long. also track/frame
        # <S><KKK><JJJ><YY><MM><DD><HH><MM><SS><I><M>: 21 cars
        #    S is the satellite number
        #    KKK and JJJ are the GRS designator of the scene (lon, lat)
        #    YY, MM, DD, HH, MM, SS are the date and time of the center of the scene 
        #    I is the instrument number
        #    M is the spectral mode of acquisition
        id = self.metadata.getMetadataValue('SOURCE_ID')
        if self.debug != 0:
            print(" product id:%s" % id)
        if id == None:
            raise Exception("no parent identifier:'%s'" % id)
        if len(id) != 21:
            raise Exception("parent identifier is not 21 cars but %d:'%s'" % (len(id), id))

        # TODO: re enable
        if 1 == 2:
            tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
            if id[0] != tmp:
                raise Exception("parent identifier/METADATA_PLATFORM_ID missmatch:%s/'%s'" % (id[0], tmp))

            tmp = self.metadata.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED)
            if id[1:4] != tmp:
                raise Exception(
                    "parent identifier/METADATA_WRS_LONGITUDE_GRID_NORMALISED missmatch:%s/'%s'" % (id[1:4], tmp))

            tmp = self.metadata.getMetadataValue(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
            if id[4:7] != tmp:
                raise Exception(
                    "parent identifier/METADATA_WRS_LATITUDE_GRID_NORMALISED missmatch:%s/'%s'" % (id[1:4], tmp))

        # check vs scene center time: 1988-10-09T11:45:36Z
        # NO:
        if 1 == 2:
            tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_TIME)
            if id[7:9] != tmp[2:4]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME YY missmatch:%s/'%s'" % (id[7:9], tmp[2:4]))
            if id[9:11] != tmp[5:7]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME MM missmatch:%s/'%s'" % (id[9:11], tmp[5:7]))
            if id[11:13] != tmp[8:10]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME DD missmatch:%s/'%s'" % (id[11:12], tmp[8:10]))
            if id[13:15] != tmp[11:13]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME HH missmatch:%s/'%s'" % (id[13:15], tmp[11:13]))
            if id[15:17] != tmp[14:16]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME MN missmatch:%s/'%s'" % (id[15:17], tmp[14:16]))
            if id[17:19] != tmp[17:19]:
                raise Exception(
                    "parent identifier/METADATA_SCENE_CENTER_TIME SS missmatch:%s/'%s'" % (id[17:19], tmp[17:19]))
            #

        # set sensor METADATA_SENSOR_OPERATIONAL_MODE == METADATA_SENSOR_CODE
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE,
                                      self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE))

        # set sensor resolution
        sensorName = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        sensorCode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE)
        if self.debug != 0:
            print(" sensorCode:%s" % sensorCode)
        # if len(sensorCode)>1:
        #    sensorCode = sensorCode[0]
        #    self.metadata.setMetadataPair(metadata.METADATA_SENSOR_CODE, sensorCode)
        resolution = self.metadata.getMetadataValue(metadata.METADATA_RESOLUTION)
        if resolution != None:
            raise Exception("FOUND a resolution:%s" % resolution)
        else:
            resolution = 20

        # build typecode
        # print("self.metadata: \n%s\n\n\n" % self.metadata.toString())
        self.buildTypeCode()

        # then fix processing level for 2A that is not allowed in the EOP schema
        # empty METADATA_REFERENCE_SYSTEM_IDENTIFIER and METADATA_REFERENCE_SYSTEM_IDENTIFIER_NAME for processingLevel != 2A
        # procLevel=self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        # if procLevel=="2A":
        #    self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, "other: 2A")
        # else:
        #    self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, "")
        #    self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, "")

        self.metadata.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)

        # set METADATA_CODESPACE_REFERENCE_SYSTEM=epsg + codespacefor non L1A products
        # if procLevel != '1A':
        #    self.metadata.addLocalAttribute(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, 'epsg')
        #    self.metadata.addLocalAttribute(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER_NAME, 'epsg:4326')

        self.metadata.addLocalAttribute('spotProfile', self.metadata.getMetadataValue(metadata.METADATA_PROFILE))

    #
    #
    #
    def extractQuality(self, helper, met):
        return 0

    #
    # extract the footprint posList point, ccw, lat lon
    # extract also the corresponding image ROW/COL 
    # prepare the browse report footprint block
    #
    def extractFootprint(self, helper, met):
        # get preview resolution
        try:
            imw, imh = imageUtil.get_image_size(self.preview_path)
            if self.debug != 0:
                print("  ## preview image size: w=%s; h=%s" % (imw, imh))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            # print "Error %s  %s\n%s" %  (exc_type, exc_obj, traceback.format_exc())
            print("#### ERROR getting preview image size: %s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc()))

        # get tiff resolution
        tmpNodes = []
        helper.getNodeByPath(None, 'Raster_Dimensions', None, tmpNodes)
        if len(tmpNodes) == 1:
            ncols = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NCOLS', None))
            nrows = helper.getNodeText(helper.getFirstNodeByPath(tmpNodes[0], 'NROWS', None))
            if self.debug != 0:
                print("  ## tiff image size: w=%s; h=%s" % (ncols, nrows))
        else:
            if self.debug != 0:
                print("#### ERROR getting tiff image size")

        rcol = int(ncols) / imw
        rrow = int(nrows) / imh
        if self.debug != 0:
            print("  ## ratio tiff/preview: rcol=%s; rrow=%s" % (rcol, rrow))

        footprint = ""
        rowCol = ""
        nodes = []
        # helper.setDebug(1)
        helper.getNodeByPath(None, 'Dataset_Frame', None, nodes)
        if len(nodes) == 1:
            vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
            if len(vertexList) == 0:
                raise Exception("can not find footprint vertex")

            # products are all descending

            # look like we get for descending:
            #
            #    3----
            #    |     ------0
            #   |
            #   |
            #  |
            #  |
            #  2-----
            #        -------1
            n = 0
            # closePoint=""
            pair = {}
            for node in vertexList:
                lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LON', None))
                lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
                if self.debug != 0:
                    print("  ############# vertex %d: lon:%s  lat:%s" % (n, lon, lat))
                # if len(footprint)>0:
                #    footprint="%s " % (footprint)
                # footprint="%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))

                # if n==0:
                #    closePoint = "%s %s" % (formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))

                pair[n] = "%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                n = n + 1
            # footprint="%s %s" % (footprint, closePoint)

            print("footprint 0:%s" % footprint)
            # set point 0 at top left corner:
            # toks = footprint.split(" ")
            # footprint = " "+ toks[] + " " + toks[]
            footprint = pair[3] + " " + pair[2] + " " + pair[1] + " " + pair[0] + " " + pair[3]
            print("footprint 1:%s" % footprint)
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

            # number of nodes in footprint
            met.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (n + 1))

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            # for SPOTVIEW calculate center
            browseIm.calculateCenter()
            lon, lat = browseIm.getCenter()
            met.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lon, lat))
            # browseIm.setColRowList(rowCol)
            print("browseIm:%s" % browseIm.info())

            if 1 == 2:
                if not browseIm.getIsCCW():
                    # keep for eolisa
                    met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

                    # and reverse
                    print("############### reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
                    browseIm.reverseFootprint()
                    # print "###############             after;%s; colRowList:%s" % (browseIm.getFootprint(), browseIm.getColRowList())
                    print("###############             after;%s" % (browseIm.getFootprint()))
                    met.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
                    met.setMetadataPair("REVERSED_FOOTPRINT", self.path)
                else:
                    met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                    # met.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, rowCol)

                    # reverse for eolisa
                    met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

                    met.setMetadataPair("NOT_REVERSED_FOOTPRINT", self.path)

            # boundingBox is needed in the localAttributes, but not for L1A
            met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
            # closedBoundingBox = "%s %s %s" % (browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
            # met.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED, browseIm.reverseSomeFootprint(closedBoundingBox))
            # no boundingbox for L1A
            processLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            # if processLevel != '1A':
            met.addLocalAttribute("boundingBox", met.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        return footprint, rowCol

    #
    #
    #
    def toString(self):
        res = "tif file:%s" % self.TIF_FILE_NAME
        res = "%s\nxml file:%s" % (res, self.XML_FILE_NAME)
        return res

    #
    #
    #
    def dump(self):
        res = "tif file:%s" % self.TIF_FILE_NAME
        res = "%s\nxml file:%s" % (res, self.XML_FILE_NAME)
        print(res)
