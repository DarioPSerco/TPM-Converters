# -*- coding: cp1252 -*-
#
# this class represent a Dimap Spot1-5 spotScene product (ZIP directory product)
#
#
#
import os
import sys
import traceback
import zipfile

from . import browse_metadata as browse_metadata
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata as metadata
from .browseImage import BrowseImage
from .product_directory import Product_Directory

# for verification
REF_TYPECODE = {'HRV__P__1A', 'HRV__P__1B', 'HRV__P__2A', 'HRV__P___3', 'HRV__X__1A', 'HRV__X__1B', 'HRV__X__2A',
                'HRV__X___3', 'HRI__M__1A', 'HRI__M__1B', 'HRI__M__2A', 'HRI__M___3', 'HRI__X__1A', 'HRI__X__2A',
                'HRI__X___3', 'HRI__I__1A', 'HRI__I__1B', 'HRI__I__2', 'HRI__I___3', 'HRG__A__1A', 'HRG__A__1B',
                'HRG__A__2A', 'HRG__B__2A', 'HRG__A___3', 'HRG__J__1A', 'HRG__J__1B', 'HRG__J__2A', 'HRG__J___3',
                'HRG__PS_1A', 'HRG__PS_1B', 'HRG__PS_2A', 'HRG__PS__3 '}


class Product_Spot_SpotScene(Product_Directory):
    PREVIEW_NAME = 'preview.jpg'
    IMAGERY_NAME = 'imagery.tif'
    METADATA_NAME = 'metadata.dim'
    EXTRACTED_PATH = None
    preview_data = None
    metadata_data = None
    preview_path = None
    metadata_path = None
    imagery_path = None

    REF_TYPECODES = [
        'HRV__P__1A', 'HRV__P__1B', 'HRV__P__2A',
        'HRV__X__1A', 'HRV__X__1B', 'HRV__X__2A',

        'HRI__M__1A', 'HRI__M__1B', 'HRI__M__2A',
        'HRI__X__1A', 'HRI__X__2A',
        'HRI__I__1A', 'HRI__I__1B', 'HRI__I__2A',

        'HRG__A__1A', 'HRG__A__1A', 'HRG__A__2A', 'HRG__B__2A',
        'HRG__J__1A', 'HRG__J__1A', 'HRG__J__2A'
    ]

    xmlMapping = {metadata.METADATA_PROFILE: 'Metadata_Id/METADATA_PROFILE',
                  metadata.METADATA_START_DATE: 'Dataset_Sources/Source_Information/Scene_Source/IMAGING_DATE',
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
                  'GEOMETRIC_PROCESSING': 'Data_Processing/GEOMETRIC_PROCESSING',
                  metadata.METADATA_SENSOR_NAME: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
                  metadata.METADATA_SENSOR_CODE: 'Dataset_Sources/Source_Information/Scene_Source/SENSOR_CODE',
                  metadata.METADATA_DATA_FILE_PATH: 'Data_Access/Data_File/DATA_FILE_PATH@href',
                  metadata.METADATA_DATASET_PRODUCTION_DATE: 'Production/DATASET_PRODUCTION_DATE',

                  metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
                  # metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE', # is manually extracted

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

        # used only for 2A and 3:
        self.has_boundingBoxAndBrowseBlock = True
        print(" init class Product_Spot_SpotScene")

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
            if name.lower().find(self.PREVIEW_NAME) >= 0:
                self.preview_path = "%s/%s" % (folder, name)
            elif name.lower().find(self.METADATA_NAME) >= 0:
                self.metadata_path = "%s/%s" % (folder, name)
            elif name.lower().find(self.IMAGERY_NAME) >= 0:
                self.imagery_path = "%s/%s" % (folder, name)

            if self.debug != 0:
                print("   %s extracted at path:%s" % (name, folder + '/' + name))
            if name.endswith('/'):
                d = d + 1
            self.contentList.append(name)

        # ESA SPOT products only have one scene in one folder
        if 1 == 1:  # new SPOT SCENE in spot6-7 folder have path starting with ./, so num folder ends up at 2. d==1:
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
        else:
            raise Exception("More than 1 directory in product:%d" % d)
        z.close()
        fh.close()

    #
    # sensor__sensorMode__level
    # list of possible typecode:
    # A)	Spot 1-3:
    # HRV__X__1A
    # HRV__p__1A
    # HRV__X__1B
    # HRV__P__1B
    # HRV__X__2A
    # HRV__P__2A
    # 
    # B)	Spot 4:
    # HRI__X__1A
    # HRI__I__1A
    # HRI__M__1A
    # HRI__M__1B
    # HRI__I__1B
    # HRI__I__2A
    # HRI__X__2A
    # 
    # C)	Spot 5:
    # HRG__J__1A
    # HRG__A__1A
    # HRG__J__1B
    # HRG__A__1B
    # HRG__J__2A
    # HRG__B__2A
    # HRG__A__2A
    #
    #
    def buildTypeCode(self):
        sensor = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        sensorCode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE)
        processLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)

        if sensor is None or sensorCode is None or processLevel is None:
            raise Exception("can not construct typecode: some field is None")

        if sensor == 'HRVIR':
            sensor = 'HRI'

        if len(sensorCode) == 1:
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, "%s__%s__%s" % (sensor, sensorCode, processLevel))
        elif len(sensorCode) == 2:
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, "%s__%s_%s" % (sensor, sensorCode, processLevel))
        else:
            raise Exception("can not construct typecode; invalid sensorCode field length:'%s'" % sensorCode)

        try:
            self.REF_TYPECODES.index(self.metadata.getMetadataValue(metadata.METADATA_TYPECODE))
        except:
            raise Exception("Unknown typedode:'%s'" % self.metadata.getMetadataValue(metadata.METADATA_TYPECODE))

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
        if not tmp.startswith('SPOTSCENE_'):
            raise Exception("not a SPOTSCENE profile but:'%s'" % tmp)

        # processing time: suppress microsec
        # is like 2017-04-28T15:59:57.557000
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos + 4]
        pos = tmp.find('Z')
        if pos < 0:
            tmp = tmp + "Z"
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        # remove eventual '-' from processing center, it break the validation
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, tmp.replace('-', '_'))

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

        # only present in spot5
        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE)
        print(("'%s'" % tmp))
        if tmp != metadata.VALUE_NOT_PRESENT:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE,
                                          formatUtils.EEEtoNumber(tmp))
        else:
            # set to 0 if not present:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE, "99")
            print("## METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE set to 99")

        # fix production date: from 2008-10-01T14:52:01.000000 to 2008-10-01T14:52:01Z
        tmp = self.metadata.getMetadataValue(metadata.METADATA_DATASET_PRODUCTION_DATE)
        pos = tmp.find('.')
        if pos > 0:
            tmp = "%sZ" % tmp[0:pos]
        self.metadata.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, tmp)

        # set scene center coordinate
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LON)
        tmp = formatUtils.EEEtoNumber(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, tmp)
        tmp1 = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LAT)
        tmp1 = formatUtils.EEEtoNumber(tmp1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, tmp1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (tmp1, tmp))

        # set scene center time, from the only we have: start time
        tmp = "%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_START_DATE),
                          self.metadata.getMetadataValue(metadata.METADATA_START_TIME))
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_TIME, tmp)
        # new:
        start = formatUtils.datePlusMsec(tmp, -4512)
        stop = formatUtils.datePlusMsec(tmp, 4512)
        # set metadata, keep 3 decimal after second
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
        # id = self.metadata.getMetadataValue(metadata.METADATA_PARENT_IDENTIFIER)
        id = self.metadata.getMetadataValue('PARENT_IDENTIFIER_BIS')
        print("## parent identifier id:%s" % id)
        if id == None:
            raise Exception("no parent identifier:'%s'" % id)
        if len(id) != 21:
            raise Exception("parent identifier is not 21 cars but %d:'%s'" % (len(id), id))

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

        # first build typecode
        self.buildTypeCode()

        # then fix processing level for 2A that is not allowed in the EOP schema
        # empty METADATA_REFERENCE_SYSTEM_IDENTIFIER and METADATA_REFERENCE_SYSTEM_IDENTIFIER_NAME for processingLevel != 2A
        procLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
        if procLevel == "2A":
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, "other: 2A")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, "")
            self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, "")

        # set sensor METADATA_SENSOR_OPERATIONAL_MODE == METADATA_SENSOR_CODE
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE,
                                      self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE))

        # set sensor resolution
        sensorName = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        sensorCode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_CODE)
        # resolution=self.metadata.getMetadataValue(metadata.METADATA_RESOLUTION)
        if sensorName == 'HRV':
            if sensorCode == 'P':
                resolution = '10'
            elif sensorCode == 'X':
                resolution = '20'
            else:
                raise Exception("for HRV resolution: unexpected sensorCode:%s" % sensorCode)
        elif sensorName == 'HRVIR':
            if sensorCode == 'M':
                resolution = '10'
            elif sensorCode == 'X':
                resolution = '20'
            elif sensorCode == 'I':
                resolution = '20'
            else:
                raise Exception("for HRVIR resolution: unexpected sensorCode:%s" % sensorCode)
        elif sensorName == 'HRG':
            if sensorCode == 'A':
                resolution = '5'
            elif sensorCode == 'B':
                resolution = '5'
            elif sensorCode == 'J':
                resolution = '20'
            else:
                raise Exception("for HRG resolution: unexpected sensorCode:%s" % sensorCode)

        self.metadata.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROFILE)
        if tmp.startswith("SPOTSCENE_"):
            self.metadata.addLocalAttribute('spotProfile', 'SPOTScene')
        else:
            raise Exception("Product has not a SPOTSCENE profile but:'%s'" % tmp)

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

            n = 0
            closePoint = ""
            closeRowCol = ""
            for node in vertexList:
                lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LON', None))
                lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
                row = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_ROW', None))
                col = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_COL', None))
                if self.debug != 0:
                    print("  ## vertex %d: lon:%s  lat:%s" % (n, lon, lat))
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

                if n == 0:
                    closePoint = "%s %s" % (formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                    closeRowCol = "%s %s" % (okRow, okCol)
                n = n + 1
            footprint = "%s %s" % (footprint, closePoint)
            rowCol = "%s %s" % (rowCol, closeRowCol)

            # number of nodes in footprint
            met.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (n + 1))

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            browseIm.setColRowList(rowCol)
            print(" browse image info:\n%s" % browseIm.info())
            if not browseIm.getIsCCW():
                # keep for eolisa
                met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

                # and reverse
                if self.debug != 0:
                    print("## reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
                browseIm.reverseFootprint()
                if self.debug != 0:
                    print("##             after;%s; colRowList:%s" % (browseIm.getFootprint(), browseIm.getColRowList()))
                met.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
                met.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, browseIm.getColRowList())
            else:
                met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                met.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, rowCol)

                # reverse for eolisa
                met.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

            # boundingBox is needed in the localAttributes
            met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
            closedBoundingBox = "%s %s %s" % (
            browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
            met.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                                browseIm.reverseSomeFootprint(closedBoundingBox))

            # boundingbox for 2A and 3 only. processing lavel is as readed
            processingLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            if processingLevel == '2A' or processingLevel == '3':
                met.addLocalAttribute("boundingBox", met.getMetadataValue(metadata.METADATA_BOUNDING_BOX))
            else:
                self.has_boundingBoxAndBrowseBlock = False

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
