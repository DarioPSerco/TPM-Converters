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
import traceback
import zipfile

from osgeo import gdal
# gdal projection transformation
from osgeo import ogr
from osgeo import osr

from . import browse_metadata
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .product_directory import Product_Directory
from xml_nodes import rep_footprint

# import eoSip_converter.fileHelper

REF_SOURCE_NAME = 'IR06_LI3_ORT_1O_20060816T094250_20060816T094312_DLR_14695_PREU.BIL.ZIP'
BROWSE_SIZE = 1400

#
REF_TYPECODE = {'SL6_L1R_1P', 'SL6_L1T_1P'}

#
REF_VERSION_NUMBER = ['P', 'S', 'T']


#
#
#
def getIrsValueFromLine(value):
    pos = value.find('>')
    pos2 = value.find('<', pos + 1)
    if pos > 0 and pos2 > pos:
        return value[pos + 1:pos2].strip()
    else:
        # pass
        raise Exception("invalid Irs value line:'%s'" % value)


# example GDAL error handler function
def gdal_error_handler(err_class, err_num, err_msg):
    errtype = {
        gdal.CE_None: 'None',
        gdal.CE_Debug: 'Debug',
        gdal.CE_Warning: 'Warning',
        gdal.CE_Failure: 'Failure',
        gdal.CE_Fatal: 'Fatal'
    }
    err_msg = err_msg.replace('\n', ' ')
    err_class = errtype.get(err_class, 'None')
    print('Error Number: %s' % err_num)
    print('Error Type: %s' % err_class)
    print('Error Message: %s' % err_msg)


#
#
#
def epsg3035to4326(lat, lon):
    gdal.PushErrorHandler(gdal_error_handler)
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(3035)
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)
    coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(lon, lat)
    point.Transform(coordTransform)
    lon1 = point.GetPoints()[0][0]
    lat1 = point.GetPoints()[0][1]
    print("EPSG:3035 lat:%s lon:%s  to EPSG:4326 lat:%s lon:%s" % (lat, lon, lon1, lat1))
    gdal.PopErrorHandler()
    return lat1, lon1


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


class Product_DmciiImage2007(Product_Directory):
    # for metadata.dim
    xmlMappingDim = {
        metadata.METADATA_PROFILE: 'Metadata_Id/METADATA_PROFILE',
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
        metadata.METADATA_GEOMETRIC_PROCESSING: 'Data_Processing/GEOMETRIC_PROCESSING',
        metadata.METADATA_PROCESSING_LEVEL: 'Data_Processing/PROCESSING_LEVEL',
        metadata.METADATA_INSTRUMENT: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
        metadata.METADATA_INSTRUMENT_ID: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT_INDEX',
        'GEOMETRIC_PROCESSING': 'Data_Processing/GEOMETRIC_PROCESSING',
        metadata.METADATA_SENSOR_NAME: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
        metadata.METADATA_SENSOR_CODE: 'Dataset_Sources/Source_Information/Scene_Source/SENSOR_CODE',
        metadata.METADATA_DATA_FILE_PATH: 'Data_Access/Data_File/DATA_FILE_PATH@href',
        metadata.METADATA_DATASET_PRODUCTION_DATE: 'Production/DATASET_PRODUCTION_DATE',

        # metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
        metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE',

        # metadata.METADATA_VIEWING_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/VIEWING_ANGLE',
        metadata.METADATA_SUN_AZIMUTH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_AZIMUTH',
        metadata.METADATA_SUN_ELEVATION: 'Dataset_Sources/Source_Information/Scene_Source/SUN_ELEVATION',
        metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Coordinate_Reference_System/Horizontal_CS/Projection/PROJECTION_CODE',

        metadata.METADATA_IMAGE_NUM_COLUMNS: 'Raster_Dimensions/NCOLS',
        metadata.METADATA_IMAGE_NUM_ROWS: 'Raster_Dimensions/NROWS',
        'LINE_PERIOD': 'Data_Strip/Sensor_Configuration/Time_Stamp/LINE_PERIOD',
        metadata.METADATA_SCENE_CENTER_TIME: 'Data_Strip/Sensor_Configuration/Time_Stamp/SCENE_CENTER_TIME',
    }

    METADATA_DIM_SUFFIX = '.dim'
    BROWSE_SUFFIX = '.jpg'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_DmciiImage2007")
        self.metadataName_dim = None
        self.metadataContent_dim = None
        self.previewName = None
        self.previewPath = None

        #
        self.isL1T = False

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
    def prepareBrowseCommands(self, processInfo):
        print(" prepareBrowseCommands")
        processInfo.addLog("    prepareBrowseCommands")
        srcPath = "%s/%s" % (processInfo.workFolder, self.previewName)
        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        print("prepareBrowseCommands: src=%s; dest=%s" % (srcPath, self.browseDestPath))
        # get src image size
        fBrowseSize = float(BROWSE_SIZE)
        width, height = imageUtil.get_size_gdal(srcPath)
        smaller = width
        if height < smaller:
            smaller = height
        ratio = 100.0 / (smaller / fBrowseSize)
        ratio = int(ratio)
        print("prepareBrowseCommands: width=%s, height=%s; ratio=%s" % (width, height, ratio))
        ratios = '%s' % ratio
        ratios = ratios + '%'
        command = ''
        # gdal_translate 
        # tmpPath =  "%s/%s__0.png" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        # command = "gdal_translate %s -outsize %s %s -of PNG %s" % (srcPath, ratios, ratios, tmpPath)

        # test: warp: is ok
        tmpPath1 = "%s/%s_0.tif" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        tmpPath2 = "%s/%s_0.png" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        # tmpPath3 =  "%s/%s_1.png" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        if not self.isSpot:
            # command = "%s\n%s" % (command, writeShellCommand("gdalwarp -s_srs EPSG:3035 -t_srs EPSG:4326 -r bilinear -ts %s 0 %s %s" % (BROWSE_SIZE, srcPath, tmpPath1), 1))
            command = "%s\n%s" % (command, writeShellCommand(
                "gdalwarp -s_srs EPSG:3035 -t_srs EPSG:4326 -r bilinear -ts %s 0 %s %s" % (
                BROWSE_SIZE, srcPath, tmpPath1), 1))
        else:
            # command = "%s\ngdal_translate -outsize %s 0 %s %s" % (command, BROWSE_SIZE, srcPath, tmpPath1)
            command = "%s\n%s" % (command, writeShellCommand(
                "gdalwarp -s_srs EPSG:3035 -t_srs EPSG:4326 -r bilinear -ts %s 0 %s %s" % (
                BROWSE_SIZE, srcPath, tmpPath1), 1))

        # new: use bands 3 2 1
        b1 = "%s/b1.tif" % processInfo.workFolder  # , processInfo.destProduct.getEoProductName())
        b2 = "%s/b2.tif" % processInfo.workFolder  # , processInfo.destProduct.getEoProductName())
        b3 = "%s/b3.tif" % processInfo.workFolder  # , processInfo.destProduct.getEoProductName())
        command = "%s\n%s" % (command, writeShellCommand("gdal_translate -b 1 %s %s" % (tmpPath1, b1), 1))
        command = "%s\n%s" % (command, writeShellCommand("gdal_translate -b 2 %s %s" % (tmpPath1, b2), 1))
        command = "%s\n%s" % (command, writeShellCommand("gdal_translate -b 3 %s %s" % (tmpPath1, b3), 1))
        tmpPath2 = "%s/%s_b321.tif" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        command = "%s\n%s" % (command, writeShellCommand(
            "gdal_merge.py -co \"PHOTOMETRIC=rgb\" -separate  %s %s %s  -o %s" % (b3, b2, b1, tmpPath2),
            1))  # self.browseDestPath)
        tmpPath3 = "%s/%s_b321.png" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        command = "%s\n%s" % (command, writeShellCommand("gdal_translate %s -of PNG %s" % (tmpPath2, tmpPath3), 1))
        # command = "%s\ngdal_translate %s -of PNG %s" % (command, tmpPath2, self.browseDestPath)
        command = "%s\n%s" % (command, writeShellCommand(
            "%s -transparent %s %s 0xff000000" % (self.stretcherAppExe, tmpPath3, self.browseDestPath), 1))

        # command = "%s\ngdal_translate %s -of PNG %s" % (command, tmpPath1, tmpPath2)

        ## stretch
        ##command = "%s\n%s -stretch %s %s 0.02" % (command, self.stretcherAppExe, tmpPath2, tmpPath3)

        #  set alpha to 235 where is above 1
        # command = "%s\n%s -thresholdAlpha %s %s 0 235" % (command, self.stretcherAppExe, tmpPath3, self.browseDestPath)

        ## rotate: not anymore because we warp
        ##angle = processInfo.srcProduct.metadata.getMetadataValue('rotation_angle')
        ##print "rotation_angle:%s" % angle
        ##command = "%s\n%s -rotate %s -in %s -out %s" % (command, self.imageutilsExe, angle, tmpPath, self.browseDestPath)
        ##print "\n\nmake browse command:\n%s\n\n\n" % command

        commandFile = "%s/command_browse.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(command)
        fd.close()
        # sys.exit(0)

    #
    #
    #
    def makeBrowses(self, processInfo):
        self.debug = True
        #
        self.prepareBrowseCommands(processInfo)
        print(" makeBrowses")
        processInfo.addLog("    makeBrowses")

        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, processInfo.destProduct.getEoProductName())
        imageUtil.makeBrowse('PNG', self.previewPath, self.browseDestPath, -1, -1, -1, None, True, 40)

        processInfo.destProduct.addSourceBrowse(self.browseDestPath, [])
        processInfo.addLog("  browse image created:%s" % self.browseDestPath)

        # create browse choice for browse metadata report
        bmet = processInfo.destProduct.browse_metadata_dict[self.browseDestPath]
        print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

        reportBuilder = rep_footprint.rep_footprint()
        #
        print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (processInfo.destProduct.metadata.toString()))
        browseChoiceBlock = reportBuilder.buildMessage(processInfo.destProduct.metadata,
                                                       "rep:browseReport/rep:browse/rep:footprint").strip()
        if self.debug != -1:
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

        processInfo.addLog("  browse image choice created:%s" % browseChoiceBlock)

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)

        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)
        # 
        n = 0
        self.isSpot = False
        self.isIrs = False
        for name in z.namelist():
            n = n + 1
            if self.debug != 0:
                print("  extract[%d]:%s" % (n, name))

            # keep metadata and preview data
            addToContent = True
            if name.find(self.METADATA_DIM_SUFFIX) >= 0:  # metadata
                self.metadataName_dim = name
                if self.debug != 0:
                    print("   metadataName_dim:%s" % name)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metadataContent_dim = data
            elif name.find(self.BROWSE_SUFFIX) >= 0:  # .bil image
                if self.debug != 0:
                    print("   browse file:%s" % name)
                self.previewName = name
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    self.previewPath = folder + '/' + name
                    outfile = open(self.previewPath, 'wb')
                    outfile.write(data)
                    outfile.close()

            else:  # need all content
                if self.debug != 0:
                    print("   file:%s" % name)
                if not name.endswith('/'):
                    data = z.read(name)
                    if dont_extract != True:
                        parent = os.path.dirname(folder + '/' + name)
                        if not os.path.exists(parent):
                            os.makedirs(parent)
                        outfile = open(folder + '/' + name, 'wb')
                        outfile.write(data)
                        outfile.close()
                    else:
                        addToContent = False

            if addToContent:
                self.contentList.append(name)

        z.close()
        fh.close()

        if self.metadataContent_dim is None:
            raise Exception("unknown product: no %s file found" % self.METADATA_DIM_SUFFIX)

    #
    #
    def buildTypeCode(self, t):
        pass

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataContent_dim is None:
            raise Exception("no metadata_xml to be parsed")

        # extact metadata
        helper = xmlHelper.XmlHelper()
        helper.setData(self.metadataContent_dim)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        print(" will extract %s metadata" % (len(list(self.xmlMappingDim.keys()))))
        for field in self.xmlMappingDim:
            print("\n ## do field[%s]:%s" % (num_added, field))
            if self.xmlMappingDim[field].find("@") >= 0:
                attr = self.xmlMappingDim[field].split('@')[1]
                path = self.xmlMappingDim[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMappingDim[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            print(" ## got field[%s]:'%s'" % (num_added, aData))

            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            print("  met[%s] -->%s=%s" % (num_added, field, aValue))

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        #
        # met.addLocalAttribute("originalName", self.origName.split('.')[0])

        # self.extractFootprint(helper, met)

        self.metadata = met

        # refine
        self.refineMetadata(helper)

        #
        self.extractFootprint(helper, met)

    #
    # refine the metada
    #
    def refineMetadata(self, xmlHelper):

        # country 2 digi
        tmp = self.origName.split('.')[0][-2:]
        self.metadata.setMetadataPair(metadata.METADATA_CITY, tmp)
        self.metadata.addLocalAttribute("country", tmp)

        # get version number
        #
        # filename is like: 20080212000000000,DU000b5eT_L1T_QL_EPSG_2942_PT
        toks = self.origName.split(',')
        if len(toks) != 2:
            raise Exception("Invalid input package name, contains no ',':%s" % self.origName)
        version = None
        if len(toks[1]) > 38:
            version = toks[1][23:24]
        else:
            version = toks[1][8:9]
        version = version.upper()
        if not version in REF_VERSION_NUMBER:
            raise Exception("invalid product version:'%s'" % version)
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, "000%s" % version)

        # METADATA_GEOMETRIC_PROCESSING
        tmp = self.metadata.getMetadataValue(metadata.METADATA_GEOMETRIC_PROCESSING)
        twoDigitGeometricProcessing = tmp[0:2]
        if twoDigitGeometricProcessing != '1T' and twoDigitGeometricProcessing != '1R':
            raise Exception("invalid twoDigitGeometricProcessing:'%s'" % twoDigitGeometricProcessing)
        self.metadata.setMetadataPair('twoDigitGeometricProcessing', twoDigitGeometricProcessing)

        # scene duration, start and stop
        LINE_PERIOD = self.metadata.getMetadataValue('LINE_PERIOD')
        center_time = "%sZ" % self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_TIME).replace(' ', 'T')
        image_height = self.metadata.getMetadataValue(metadata.METADATA_IMAGE_NUM_ROWS)
        duration = float(LINE_PERIOD) * int(image_height) * 1000
        print((" duration msec=%s" % duration))

        # get start/stop date + time with no msec
        start = formatUtils.datePlusMsec(center_time, -(duration / 2),
                                         pattern=formatUtils.DEFAULT_DATE_PATTERN)  # return full dateTtimeZ
        # print(" start=%s" % (start))

        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].split('.')[0])

        stop = formatUtils.datePlusMsec(center_time, duration / 2, pattern=formatUtils.DEFAULT_DATE_PATTERN)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].split('.')[0])

        print((" start=%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_START_DATE),
                                 self.metadata.getMetadataValue(metadata.METADATA_START_TIME))))
        print((" stop=%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
                                self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME))))
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # add time to metadata.METADATA_PROCESSING_TIME
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if len(tmp) == 10:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, "%sT00:00:00Z" % tmp)

        # do we have ORBIT?
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        print(("orbit:%s; type;%s" % (tmp, type(tmp))))
        if tmp is None:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, 0)

        # set platform name as requested in spec
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        if tmp.lower() == 'beijing':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'Beijing')
        elif tmp.lower() == 'uk-dmc':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'UK-DMC')
        elif tmp.lower() == 'nigeriasat':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'NigeriaSat')
        else:
            raise Exception("unknown METADATA_PLATFORM:'%s'" % tmp)

        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        toks = tmp.split(' ')
        if toks[0] == 'SLIM-6':
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'SLIM6')
            if twoDigitGeometricProcessing == '1T':
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'SL6_LIT_1P')
                self.isL1T = True
            else:
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'SL6_LIR_1P')
        else:
            raise Exception("sensor name not recognized:'%s'" % tmp)

        # sys.exit(0)
        print("DUMP:\n%s" % self.metadata.toString())

    #
    # extract the footprint posList point, ccw, lat lon
    # extract also the corresponding image ROW/COL
    # prepare the browse report footprint block
    #
    def extractFootprint(self, helper, met):
        # get preview resolution
        try:
            imw, imh = imageUtil.get_image_size(self.previewPath)
            if self.debug != 10:
                print("  ############# preview image size: w=%s; h=%s" % (imw, imh))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            # print "Error %s  %s\n%s" %  (exc_type, exc_obj, traceback.format_exc())
            print("###################### ERROR getting preview image size: %s  %s\n%s" % (
                exc_type, exc_obj, traceback.format_exc()))

        # get tiff resolution
        ncols = met.getMetadataValue(metadata.METADATA_IMAGE_NUM_COLUMNS)
        ncols = int(ncols)
        nrows = met.getMetadataValue(metadata.METADATA_IMAGE_NUM_ROWS)
        image_height = int(nrows)
        print("image_width: %s image_height: %s" % (ncols, nrows))

        rcol = int(ncols) / imw
        rrow = int(nrows) / imh
        print("  ############# ratio tiff/preview: rcol=%s; rrow=%s" % (rcol, rrow))

        footprint = ""
        rowCol = ""
        nodes = []
        # helper.setDebug(1)
        helper.getNodeByPath(None, 'Dataset_Frame', None, nodes)
        # helper.getNodeByPath(None, 'Dataset_Sources/Source_Information/Source_Frame', None, nodes)
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
                # two cases : FRAME_LON and FRAME_Y nodes
                lon = None
                lat = None
                lonNode = helper.getFirstNodeByPath(node, 'FRAME_LON', None)
                if lonNode is not None:
                    lon = helper.getNodeText(lonNode)
                    lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
                else:
                    lonNode = helper.getFirstNodeByPath(node, 'FRAME_X', None)
                    if lonNode is not None:
                        # verify  unit attribute is DEB
                        unit = helper.getNodeAttributeText(lonNode, 'unit')
                        if unit is None:
                            raise Exception("cannot find Dataset_Frame LON/LAT nodes: unit attribute not found")
                        else:
                            if unit != 'DEG':
                                raise Exception(
                                    "cannot find Dataset_Frame LON/LAT nodes: unit attribute is not 'DEG' but:'%s'" % unit)
                        lon = helper.getNodeText(lonNode)
                        lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_Y', None))
                    else:
                        raise Exception("cannot find Dataset_Frame LON/LAT nodes")

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

            # set point 0 at top left corner:
            # toks = footprint.split(" ")
            # footprint = " "+ toks[] + " " + toks[]
            footprint = pair[3] + " " + pair[2] + " " + pair[1] + " " + pair[0] + " " + pair[3]
            print("footprint 1:%s" % footprint)
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

            # os._exit(1)

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
            met.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % lat)
            met.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % lon)

            flon = float(lon)
            flat = float(lat)
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
            met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
            met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
            met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
            met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

            met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)
            met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)

            # browseIm.setColRowList(rowCol)
            print("browseIm:%s" % browseIm.info())

            met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
            if self.isL1T:
                met.addLocalAttribute("boundingBox", met.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        else:
            raise Exception("invalid Source_Frame length:%s" % len(nodes))

        return footprint, rowCol

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    # for SPOT, as in dimap_spot_product.py
    #
    def extractFootprintSpot_NOT_USED(self, helper):
        self.debug = True
        footprint = ""
        nodes = []
        # helper.setDebug(1)
        helper.getNodeByPath(None, 'Dataset_Frame', None, nodes)
        if len(nodes) == 1:
            vertexList = helper.getNodeChildrenByName(nodes[0], 'Vertex')
            if len(vertexList) == 0:
                raise Exception("can not find footprint vertex")

            n = 0
            closePoint = ""
            for node in vertexList:
                lon = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LON', None))
                lat = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_LAT', None))
                row = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_ROW', None))
                col = helper.getNodeText(helper.getFirstNodeByPath(node, 'FRAME_COL', None))
                if self.debug != 0:
                    print("  ############# vertex %d: lon:%s  lat:%s" % (n, lon, lat))
                if len(footprint) > 0:
                    footprint = "%s " % footprint
                footprint = "%s%s %s" % (footprint, formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))

                if n == 0:
                    closePoint = "%s %s" % (formatUtils.EEEtoNumber(lat), formatUtils.EEEtoNumber(lon))
                n = n + 1

            footprint = "%s %s" % (footprint, closePoint)

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            # get scene center
            clat, clon = browseIm.calculateCenter()
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)

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
            browseIm.calculateBoondingBox()
            print("browseIm:%s" % browseIm.info())
            if not browseIm.getIsCCW():
                # keep for eolisa
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

                # and reverse
                print("############### reverse the footprint; before:%s" % footprint)
                browseIm.reverseFootprint()
                print("###############             after;%s; colRowList:%s" % (
                browseIm.getFootprint(), browseIm.getColRowList()))
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())

            else:
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

                # reverse for eolisa
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

            # boundingBox is needed in the localAttributes
            # use geoBB
            # tmp = self.metadata.getMetadataValue('geoBB')
            # print "use geoBB:%s instead of footprint bbox" % tmp
            # sys.exit(1)
            #
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
            closedBoundingBox = "%s %s %s" % (
            browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                                          browseIm.reverseSomeFootprint(closedBoundingBox))
            self.metadata.addLocalAttribute("boundingBox",
                                            self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        # os._exit(1)

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
