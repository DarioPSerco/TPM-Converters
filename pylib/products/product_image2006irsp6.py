# -*- coding: cp1252 -*-
#
# this class represent a worldview directory product
#
#  - 
#  - 
#
#
import math
import os
import shutil
import zipfile
from subprocess import call

from osgeo import gdal
# gdal projection transformation
from osgeo import ogr
from osgeo import osr

from . import browse_metadata
import eoSip_converter.geomHelper as geomHelper
import eoSip_converter.imageUtil as imageUtil
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .product_directory import Product_Directory
from xml_nodes import rep_footprint
from xml_nodes import sipBuilder

# import eoSip_converter.fileHelper

REF_SOURCE_NAME = 'IR06_LI3_ORT_1O_20060816T094250_20060816T094312_DLR_14695_PREU.BIL.ZIP'
BROWSE_SIZE = 1400

REF_TYPECODE = {'LI3_ORT_20', 'HRI__X__20', 'HRG__X__20'}


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


class Product_Image2006IrsP6(Product_Directory):
    # for metadata.xml
    xmlMapping = {metadata.METADATA_ORIGINAL_NAME: 'Production/DATASET_NAME',
                  metadata.METADATA_SENSOR_NAME: 'Production/DATASET_SENSOR',
                  metadata.METADATA_PROCESSING_TIME: 'Production/DATASET_PRODUCTION_DATE',
                  metadata.METADATA_COUNTRY: 'Production/DATASET_COUNTRY',
                  'origin': 'Production/DATASET_ORIGIN',
                  'production_type': 'DATASET_PRODUCTION_TYPE',
                  'image_width': 'Image/COLUMNS',
                  'image_height': 'Image/ROWS',
                  'XGEOREF': 'GeoInformation/XGEOREF',
                  'YGEOREF': 'GeoInformation/YGEOREF',
                  'XCELLRES': 'GeoInformation/XCELLRES',
                  'YCELLRES': 'GeoInformation/YCELLRES'
                  }

    # for SPOT metadata.dim
    xmlMapping2 = {
        metadata.METADATA_INSTRUMENT: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT',
        metadata.METADATA_INSTRUMENT_ID: 'Dataset_Sources/Source_Information/Scene_Source/INSTRUMENT_INDEX',
        metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'Dataset_Sources/Source_Information/Scene_Source/SENSOR_CODE',
        metadata.METADATA_PROCESSING_LEVEL: 'Dataset_Sources/Source_Information/Scene_Source/SCENE_PROCESSING_LEVEL',
        metadata.METADATA_SUN_AZIMUTH: 'Dataset_Sources/Source_Information/Scene_Source/SUN_AZIMUTH',
        metadata.METADATA_SUN_ELEVATION: 'Dataset_Sources/Source_Information/Scene_Source/SUN_ELEVATION',
        metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'Dataset_Sources/Source_Information/Scene_Source/INCIDENCE_ANGLE',
        metadata.METADATA_PROCESSING_TIME: 'Production/DATASET_PRODUCTION_DATE',
        metadata.METADATA_SOFTWARE_NAME: 'Production/Production_Facility/SOFTWARE_NAME',
        metadata.METADATA_SOFTWARE_VERSION: 'Production/Production_Facility/SOFTWARE_VERSION',
        'rotation_angle': 'Dataset_Frame/SCENE_ORIENTATION'
    }

    # for IRS P6
    irsMapping = {metadata.METADATA_ORBIT: ' 48  518  525 I8   ',
                  metadata.METADATA_SUN_AZIMUTH: ' 51  574  589 F16.7',
                  metadata.METADATA_SUN_ELEVATION: ' 52  590  605 F16.7',
                  'clat': ' 10  101  116 F16.7',
                  'clong': ' 11  117  132 F16.7',
                  'TOPLEFTLAT': ' 14  149  164 F16.7',
                  'TOPLEFTLON': ' 15  165  180 F16,7',

                  'TOPRIGHTLAT': ' 18  197  212 F16.7',
                  'TOPRIGHTLON': ' 19  213  228 F16,7',

                  'BOTTOMLEFTLAT': ' 22  245  260 F16.7',
                  'BOTTOMLEFTLON': ' 23  261  276 F16,7',

                  'BOTTOMRIGHTLAT': ' 26  293  308 F16.7',
                  'BOTTOMRIGHTLON': ' 27  309  324 F16,7',

                  metadata.METADATA_SOFTWARE_VERSION: '  9   33   44 A12'
                  }

    METADATA_DIM = '.dim'
    METADATA_XML = '.xml'
    METADATA_TXT = '_ssd.txt'
    IMAGE = 'imagery.bil'

    SPOT_VERSION_LUT = {'07-01': '701', '07-02': '702', 'SPOT5_V07-01CP1': '701', 'SPOT5_V07_01CP1': '701',
                        'SPOT5_v07-02': '702', 'SPOT5_V07_02': '702', }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_Image2006IrsP6")
        self.metadataName_xml = None
        self.metadataContent_xml = None
        self.metadataName_dim = None
        self.metadataContent_dim = None
        self.metadataName_txt = None
        self.metadataContent_txt = None
        self.imageName = None

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
        srcPath = "%s/%s" % (processInfo.workFolder, self.imageName)
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

        # launch the main make_browse script:
        command = "/bin/sh -f %s/command_browse.sh" % processInfo.workFolder
        # 
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        # crop util pixels for IRSP6
        if not self.isSpot or 1 == 1:
            width, height = imageUtil.get_image_size(self.browseDestPath)
            print("will crop image: width=%s; height=%s; xRatio=%s; yRatio=%s" % (
            width, height, self.xRatio, self.yRatio))
            nHeight = math.ceil(height * self.yRatio)
            nWidth = math.ceil(width * self.xRatio)
            #
            # toCutX = width - nWidth
            # toCutY = height - nHeight
            toCutX = width - int(width * self.xRatio)
            toCutY = height - int(height * self.yRatio)
            #
            left = toCutX / 2.0
            top = toCutY / 2.0
            print("will crop image 0: left=%s; top=%s; nWidth=%s; nHeight=%s" % (left, top, nWidth, nHeight))
            processInfo.addLog("######## will crop image %s: left=%s; top=%s; nWidth=%s; nHeight=%s" % (
            self.browseDestPath, left, top, nWidth, nHeight))
            #
            # NO: util zone may not be centered
            #
            print("leftDist=%s; rightDist=%s; topDist=%s; bottomDist=%s" % (
            self.leftDist, self.rightDist, self.topDist, self.bottomDist))
            b = int(toCutX / ((self.leftDist / self.rightDist) + 1))
            a = toCutX - b - 1

            d = int(toCutY / ((self.topDist / self.bottomDist) + 1))
            c = toCutY - d - 1

            left = toCutX * self.leftDist / self.rightDist
            top = top * self.topDist / self.bottomDist
            print("will crop image 1: left=%s; top=%s; nWidth=%s; nHeight=%s" % (left, top, nWidth, nHeight))
            print("will crop image 2: a=%s; c=%s" % (a, c))

            shutil.copyfile(self.browseDestPath, "%s/%s" % (processInfo.workFolder, 'before_crop.png'))
            # print "will crop image: left=%s; top=%s; nWidth=%s; nHeight=%s" % (left, top, nWidth, nHeight)
            # imageUtil.cropImage(self.browseDestPath, "%s/%s" % (processInfo.workFolder, 'cropped.png'), int(left), int(top), int(nWidth), int(nHeight), 'PNG')
            print("will crop image: left=%s; top=%s; nWidth=%s; nHeight=%s" % (a, c, nWidth, nHeight))
            imageUtil.cropImage(self.browseDestPath, "%s/%s" % (processInfo.workFolder, 'cropped.png'), int(a), int(c),
                                int(nWidth), int(nHeight), 'PNG')
            shutil.copyfile("%s/%s" % (processInfo.workFolder, 'cropped.png'), self.browseDestPath)
        # sys.exit(0)

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
            if name.find(self.METADATA_DIM) >= 0:  # metadata
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
            elif name.find(self.METADATA_XML) >= 0:  # metadata
                self.metadataName_xml = name
                if self.debug != 0:
                    print("   metadataName_xml:%s" % name)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metadataContent_xml = data
            elif name.find(self.METADATA_TXT) >= 0:  # metadata
                self.metadataName_txt = name
                if self.debug != 0:
                    print("   metadataName_txt:%s" % name)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metadataContent_txt = data
            elif name.find(self.IMAGE) >= 0:  # .bil image
                if self.debug != 0:
                    print("   image file:%s" % name)
                self.imageName = name
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                # addToContent=False
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

        if self.metadataName_xml is None:
            raise Exception("unknown product: metadata.xml not found")

    #
    # LI3_ORT_20
    # HRI__X__20
    # HRG__X__20
    #
    def buildTypeCode(self, t):
        plat = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        if plat == 'SPOT':
            platid = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
            if platid == '4':
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'HRI__X__2O')
            elif platid == '5':
                self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'HRG__X__2O')
                # as by AS: set to HRG
                self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'HRG')
            else:
                raise Exception("unknown platform id:%s" % platid)
        elif plat[0:2] == 'LI':
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'LI3_ORT_2O')
        else:
            raise Exception("unknown platform:%s" % plat)

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataContent_xml is None:
            raise Exception("no metadata_xml to be parsed")

        # extact metadata
        helper = xmlHelper.XmlHelper()
        helper.setData(self.metadataContent_xml)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.xmlMapping:
            print("######################## do field[%s]:%s" % (num_added, field))
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            print("######################## will get metadata field")
            aData = helper.getFirstNodeByPath(None, path, None)
            print("######################## got field[%s]:'%s'" % (num_added, aData))

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
        met.addLocalAttribute("originalName", self.origName)

        self.metadata = met

        # refine
        self.refineMetadata(helper)

    #
    # extract irsp6 metadata
    #
    def extractMetadataIrs(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataContent_txt is None:
            raise Exception("no metadata_dim to be parsed")

        lines = self.metadataContent_txt.split('\n')
        print("Irs metadata file contains:%s lines" % len(lines))

        # extact metadata
        num_added = 0
        for field in self.irsMapping:
            print("######################## do field[%s]:%s" % (num_added, field))
            key = self.irsMapping[field]

            for line in lines:
                if line.startswith(key):
                    aValue = getIrsValueFromLine(line[len(key):])
                    print("  met[%s] -->%s or %s value:'%s'" % (num_added, field, key, aValue))
                    met.setMetadataPair(field, aValue)
                    num_added += 1
                    break

        print("######################## num_added:%s" % num_added)

        # instrument: fixed
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'LISS-3')
        # metadata.METADATA_PROCESSING_TIME, like: 2007-07-24
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if len(tmp) == len('2007-07-24'):
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, "%sT00:00:00Z" % tmp)
        else:
            raise Exception("unexped processing time format:'%s'" % tmp)
        # 2007-10-26

        clat = self.metadata.getMetadataValue('clat')
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, clat)
        clon = self.metadata.getMetadataValue('clong')
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

        #
        footprint = '%s %s' % (
        self.metadata.getMetadataValue('TOPLEFTLAT'), self.metadata.getMetadataValue('TOPLEFTLON'))
        footprint = '%s %s %s' % (
        footprint, self.metadata.getMetadataValue('BOTTOMLEFTLAT'), self.metadata.getMetadataValue('BOTTOMLEFTLON'))
        footprint = '%s %s %s' % (
        footprint, self.metadata.getMetadataValue('BOTTOMRIGHTLAT'), self.metadata.getMetadataValue('BOTTOMRIGHTLON'))
        footprint = '%s %s %s' % (
        footprint, self.metadata.getMetadataValue('TOPRIGHTLAT'), self.metadata.getMetadataValue('TOPRIGHTLON'))
        footprint = '%s %s %s' % (
        footprint, self.metadata.getMetadataValue('TOPLEFTLAT'), self.metadata.getMetadataValue('TOPLEFTLON'))
        print("FOOTPRINT:%s" % footprint)
        # sys.exit(0)
        # self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
        self.metadata.setMetadataPair('utilPixelsFootprint', footprint)

        browseIm = BrowseImage()
        browseIm.setFootprint(footprint)
        # get scene center
        clat2, clon2 = browseIm.calculateCenter()
        browseIm.calculateBoondingBox()
        self.metadata.setMetadataPair('utilPixelsBoundingBox', browseIm.boondingBox)
        self.metadata.addLocalAttribute("boundingBox", browseIm.boondingBox)
        # self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        # self.metadata.addLocalAttribute("boundingBox", self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        # software version like:IRSP6DPSV1R2
        version = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        fileVersion = version.replace('IRSP6DPSV', '').replace('R', '')
        print("version:'%s'; fileVersion0:'%s'" % (version, fileVersion))
        if len(fileVersion) > 3:
            if fileVersion[0] == '0':
                fileVersion = fileVersion[1:]
            if fileVersion[0] == '0':
                fileVersion = fileVersion[0:3]
        elif len(fileVersion) < 3:
            fileVersion = formatUtils.leftPadString(fileVersion, 3, '0')
        # print "fileVersion1:'%s'" % fileVersion

        counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        if counter is None or counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:  # counter==sipBuilder.VALUE_NONE:
            counter = '1'
        else:
            print("counter is present:'%s'" % counter)

        self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                      "%s%s" % (fileVersion, counter))  # in the sip package name
        # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version) # in the MD
        # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version.replace('IRSP6DPSV','')) # not used
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, 'IRSP6DPSV')
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, version.replace('IRSP6DPSV', ''))

        # if self.DEBUG!=0:
        # print " version:%s; fileVersion:%s" % (version, fileVersion)

        # set IRSP6 METADATA_PLATFORM_2DIGITS_ALIAS=WV
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, 'IP')
        # sys.exit(0)

    #
    # for spot?
    #
    def extractMetadataDim(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataContent_dim is None:
            raise Exception("no metadata_dim to be parsed")

        # extact metadata
        helper = xmlHelper.XmlHelper()
        helper.setData(self.metadataContent_dim)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.xmlMapping2:
            print("######################## do field[%s]:%s" % (num_added, field))
            if self.xmlMapping2[field].find("@") >= 0:
                attr = self.xmlMapping2[field].split('@')[1]
                path = self.xmlMapping2[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping2[field]

            aData = helper.getFirstNodeByPath(None, path, None)

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

        # extract software version from dim file
        # path='Production/Production_Facility/SOFTWARE_VERSION' # like: 07-02
        # resultList=[]
        # helper.getNodeByPath(None, path, None, resultList)
        version = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        if version != None:  #
            if version not in self.SPOT_VERSION_LUT:
                raise Exception("unexpected dataset version:%s" % version)

            fileVersion = self.SPOT_VERSION_LUT[version]
            counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
            if counter is None or counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:  # counter==sipBuilder.VALUE_NONE:
                counter = '1'
            else:
                print("counter is present:'%s'" % counter)

            self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                          "%s%s" % (fileVersion, counter))  # in the sip package name
            # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version) # in the MD
            self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, fileVersion)  # in the MD
            self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, fileVersion)  # in the MD
            if self.debug != 0:
                print(" version:%s; fileVersion:%s" % (version, fileVersion))

            if 1 == 2:
                fileVersion = version.replace('-', '')
                if len(fileVersion) > 3:
                    if fileVersion[0] == '0':
                        fileVersion = fileVersion[1:]
                    if fileVersion[0] == '0':
                        fileVersion = fileVersion[0:3]
                elif len(fileVersion) < 3:
                    fileVersion = formatUtils.leftPadString(fileVersion, 3, '0')

                counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
                if counter is None or counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:  # counter==sipBuilder.VALUE_NONE:
                    counter = '1'
                else:
                    print("counter is present:'%s'" % counter)

                self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                              "%s%s" % (fileVersion, counter))  # in the sip package name
                self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)  # in the MD
                if self.debug != 0:
                    print(" version:%s; fileVersion:%s" % (version, fileVersion))
        else:
            # raise Exception("can not retrieve dataset version")
            raise Exception("strange software version:'%s'" % version)
            # default to zero
            fileVersion = '000'
            version = '000'
            counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
            if counter is None or counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:
                counter = '1'
            else:
                print("counter is present:'%s'" % counter)

            self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                          "%s%s" % (fileVersion, counter))  # in the sip package name
            self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)  # in the MD
            if self.debug != 0:
                print(" version defaulted to:%s; fileVersion:%s" % (version, fileVersion))

        # extract the footprint
        self.extractFootprintSpot(helper)

        # change EEEtoNumber to number
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_AZIMUTH)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_ELEVATION)
        self.metadata.setMetadataPair(metadata.METADATA_SUN_ELEVATION, formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, formatUtils.EEEtoNumber(tmp))

        tmp = self.metadata.getMetadataValue('rotation_angle')
        self.metadata.setMetadataPair('rotation_angle', formatUtils.EEEtoNumber(tmp))

        # metadata.METADATA_PROCESSING_TIME, like: 2007-07-24T14:47:06.000000
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos]
        # print "TMP:'%s'" % tmp
        if tmp[-1] != 'Z':
            tmp = "%sZ" % tmp
        if len(tmp) != len('2007-07-24T14:47:06Z'):
            raise Exception("invalid METADATA_PROCESSING_TIME:'%s'" % tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)
        # not available in metadata: si
        # self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME,'')
        # self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, '')

    #
    # refine the metada
    #
    def refineMetadata(self, xmlHelper):
        # start/stop/typecode from DATASET_NAME like 'IR06_LI3_ORT_1O_20060816T094250_20060816T094312_DLR_14695_PREU.BIL.ZIP'
        # or:                                        'SP04_HRV2_X__1O_20051016T094203_20051016T094212_DLR_113_PREU.BIL.ZIP'
        # or:                                         'SP04_HRV2_X__1O_20051016T094203_20051016T094212_DLR_113_0000.BIL.ZIP'
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
        fixedPart = tmp[0:52]  # SP04_HRV2_X__1O_20051016T094203_20051016T094212_DLR_
        variablePart = tmp[52:]
        print("'%s'; '%s'" % (fixedPart, variablePart))
        toks = variablePart.split('_')
        if toks[1].upper() != 'PREU.BIL.ZIP' and toks[1].upper() != '0000.BIL.ZIP':
            raise Exception("source product not recognized: strange suffix:'%s'" % variablePart)

        if fixedPart[0:4] != 'IR06' and fixedPart[0:4] != 'SP04' and fixedPart[0:4] != 'SP05':
            raise Exception("source product not recognized:'%s'" % tmp)

        if fixedPart[0:4] == 'SP04' or fixedPart[0:4] == 'SP05':
            self.isSpot = True
            # extract K/J info from origin like: 10223228810091145361X
            # SPOT has GRS (K, J) pair. J is lat. K is long. also track/frame
            # <S><KKK><JJJ><YY><MM><DD><HH><MM><SS><I><M>: 21 cars
            #    S is the satellite number
            #    KKK and JJJ are the GRS designator of the scene (lon, lat)
            #    YY, MM, DD, HH, MM, SS are the date and time of the center of the scene 
            #    I is the instrument number
            #    M is the spectral mode of acquisition
            tmp = self.metadata.getMetadataValue('origin')
            self.metadata.setMetadataPair(metadata.METADATA_TRACK, tmp[1:4])
            self.metadata.setMetadataPair(metadata.METADATA_FRAME, tmp[4:7])

            # extract metadata from dim file
            self.extractMetadataDim(self.metadata)

        elif fixedPart[0:4] == 'IR06':
            self.isIrs = True
            self.extractMetadataIrs(self.metadata)

        # start stop date time
        startdateTime = fixedPart[16:31]
        stoptdateTime = fixedPart[32:47]
        typecode = fixedPart[5:15]
        print("typecode:%s; startdateTime:%s; stoptdateTime:%s" % (typecode, startdateTime, stoptdateTime))

        self.metadata.setMetadataPair(metadata.METADATA_START_DATE,
                                      "%s-%s-%s" % (startdateTime[0:4], startdateTime[4:6], startdateTime[6:8]))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE,
                                      "%s-%s-%s" % (stoptdateTime[0:4], stoptdateTime[4:6], stoptdateTime[6:8]))
        #
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME,
                                      "%s:%s:%s" % (startdateTime[9:11], startdateTime[11:13], startdateTime[13:15]))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME,
                                      "%s:%s:%s" % (stoptdateTime[9:11], stoptdateTime[11:13], stoptdateTime[13:15]))
        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # platform sensor: IRS-P6-LISS III or SPOT 4
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        toks = tmp.split(' ')
        if toks[0] == 'SPOT':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, toks[0])
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, toks[1])
        elif toks[0] == 'IRS-P6-LISS':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'IRS-P6')
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID,
                                          '6')  # will be change at N/A in beforeReportsDone()
        else:
            raise Exception("sensor name not recognized:'%s'" % tmp)

        self.buildTypeCode(typecode)

        # country in local attributes
        self.metadata.addLocalAttribute("country", self.metadata.getMetadataValue(metadata.METADATA_COUNTRY))

        image_width = self.metadata.getMetadataValue('image_width')
        image_width = int(image_width)
        image_height = self.metadata.getMetadataValue('image_height')
        image_height = int(image_height)
        print("image_width: %s image_height: %s" % (image_width, image_height))

        # keep product 'source footprint', util pixels?
        source_footprint = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        print("SOURCE FOOTPRINT:%s" % source_footprint)
        self.metadata.setMetadataPair('source_footprint', source_footprint)

        source_bbox = self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)
        print("SOURCE BBOX:%s" % source_bbox)
        self.metadata.setMetadataPair('source_bbox', source_bbox)

        # geoinfo
        #        'XGEOREF':'GeoInformation/XGEOREF',
        #        'YGEOREF':'GeoInformation/YGEOREF',
        #        'XCELLRES':'GeoInformation/XCELLRES',
        #        'YCELLRES':'GeoInformation/YCELLRES'
        xgeo = self.metadata.getMetadataValue('XGEOREF')
        ygeo = self.metadata.getMetadataValue('YGEOREF')
        xres = self.metadata.getMetadataValue('XCELLRES')
        xres = float(xres)
        yres = self.metadata.getMetadataValue('YCELLRES')
        yres = float(yres)
        print("geoinfo: %s %s %s %s" % (xgeo, ygeo, xres, yres))

        tl_x = float(xgeo)
        tl_y = float(ygeo)

        tr_x = tl_x + image_width * xres
        tr_y = tl_y

        bl_x = tl_x
        bl_y = tl_y - image_height * yres

        br_x = bl_x + image_width * xres
        br_y = tr_y - image_height * yres
        print("tl_x:%s tl_y:%s" % (tl_x, tl_y))
        print("bl_x:%s bl_y:%s" % (bl_x, bl_y))
        print("br_x:%s br_y:%s" % (br_x, br_y))
        print("tr_x:%s tr_y:%s" % (tr_x, tr_y))

        # transform:
        tl_lat, tl_lon = epsg3035to4326(tl_y, tl_x)
        print("tl_lat:%s tl_lon:%s" % (tl_lat, tl_lon))

        tl_lat, tl_lon = epsg3035to4326(tl_y, tl_x)
        bl_lat, bl_lon = epsg3035to4326(bl_y, bl_x)
        br_lat, br_lon = epsg3035to4326(br_y, br_x)
        tr_lat, tr_lon = epsg3035to4326(tr_y, tr_x)
        geoFootprint = "%s %s %s %s %s %s %s %s %s %s" % (
        tl_lat, tl_lon, bl_lat, bl_lon, br_lat, br_lon, tr_lat, tr_lon, tl_lat, tl_lon)
        self.metadata.setMetadataPair("geoFootprint", geoFootprint)
        print("geoFootprint:%s" % geoFootprint)

        browseIm = BrowseImage()
        browseIm.setFootprint(geoFootprint)
        browseIm.calculateBoondingBox()
        # this is ok for spot
        if self.isSpot and 1 == 1:  # strange_spot_browse_pb_test
            self.metadata.setMetadataPair('geoBB', browseIm.boondingBox)
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
            print("geoBB:%s" % browseIm.boondingBox)

            # new: some spot browse pb: do like for IRSP6
            tmp = browseIm.boondingBox
            print("\n\nBIG BBOX:%s" % tmp)
            toks = tmp.split(' ')
            # for SPOT? we want to cut the browse image at the util pixels boundingbox
            # first get the too big boundingBox
            xRad = geomHelper.sphericalDistance(float(toks[0]), float(toks[1]), float(toks[6]), float(toks[7]))
            yRad = geomHelper.sphericalDistance(float(toks[0]), float(toks[1]), float(toks[2]), float(toks[3]))
            xDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[6]), float(toks[7]))
            yDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[2]), float(toks[3]))
            print("bigBB xRad=%s; yRad=%s; xDist:%s; yDist=%s" % (xRad, yRad, xDist, yDist))
            # then the util bbox
            tmp = source_bbox
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, source_bbox)
            print("\n\nSMALL BBOX:%s" % tmp)
            toks2 = tmp.split(' ')
            sxRad = geomHelper.sphericalDistance(float(toks2[0]), float(toks2[1]), float(toks2[6]), float(toks2[7]))
            syRad = geomHelper.sphericalDistance(float(toks2[0]), float(toks2[1]), float(toks2[2]), float(toks2[3]))
            sxDist = geomHelper.metersDistanceBetween(float(toks2[0]), float(toks2[1]), float(toks2[6]),
                                                      float(toks2[7]))
            syDist = geomHelper.metersDistanceBetween(float(toks2[0]), float(toks2[1]), float(toks2[2]),
                                                      float(toks2[3]))
            print("smallBB sxRad=%s; syRad=%s; sxDist:%s; syDist=%s" % (sxRad, syRad, sxDist, syDist))
            self.xRatio = sxDist / xDist
            self.yRatio = syDist / yDist
            print("xRatio=%s; yRatio=%s\n\n\n" % (self.xRatio, self.yRatio))
            # BUT it look like the util part may not be centered
            self.leftDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[0]),
                                                             float(toks2[1]))
            self.rightDist = geomHelper.metersDistanceBetween(float(toks[6]), float(toks[7]), float(toks[6]),
                                                              float(toks2[7]))
            self.topDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks2[0]),
                                                            float(toks[1]))
            self.bottomDist = geomHelper.metersDistanceBetween(float(toks[2]), float(toks[3]), float(toks2[2]),
                                                               float(toks[3]))
            print("leftDist=%s; rightDist=%s; topDist=%s; bottomDist=%s\n\n\n" % (
            self.leftDist, self.rightDist, self.topDist, self.bottomDist))

        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
            tmp = browseIm.boondingBox
            print("\n\nBIG BBOX:%s" % tmp)
            toks = tmp.split(' ')
            # for IRSP6 we want to cut the browse image at the util pixels boundingbox
            # first get the too big boundingBox
            xRad = geomHelper.sphericalDistance(float(toks[0]), float(toks[1]), float(toks[6]), float(toks[7]))
            yRad = geomHelper.sphericalDistance(float(toks[0]), float(toks[1]), float(toks[2]), float(toks[3]))
            xDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[6]), float(toks[7]))
            yDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[2]), float(toks[3]))
            print("bigBB xRad=%s; yRad=%s; xDist:%s; yDist=%s" % (xRad, yRad, xDist, yDist))
            # then the util bbox
            tmp = self.metadata.getMetadataValue('utilPixelsBoundingBox')
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, tmp)
            print("\n\nSMALL BBOX:%s" % tmp)
            toks2 = tmp.split(' ')
            sxRad = geomHelper.sphericalDistance(float(toks2[0]), float(toks2[1]), float(toks2[6]), float(toks2[7]))
            syRad = geomHelper.sphericalDistance(float(toks2[0]), float(toks2[1]), float(toks2[2]), float(toks2[3]))
            sxDist = geomHelper.metersDistanceBetween(float(toks2[0]), float(toks2[1]), float(toks2[6]),
                                                      float(toks2[7]))
            syDist = geomHelper.metersDistanceBetween(float(toks2[0]), float(toks2[1]), float(toks2[2]),
                                                      float(toks2[3]))
            print("smallBB sxRad=%s; syRad=%s; sxDist:%s; syDist=%s" % (sxRad, syRad, sxDist, syDist))
            self.xRatio = sxDist / xDist
            self.yRatio = syDist / yDist
            print("xRatio=%s; yRatio=%s\n\n\n" % (self.xRatio, self.yRatio))
            # BUT it look like the util part may not be centered
            self.leftDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[0]),
                                                             float(toks2[1]))
            self.rightDist = geomHelper.metersDistanceBetween(float(toks[6]), float(toks[7]), float(toks[6]),
                                                              float(toks2[7]))
            self.topDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks2[0]),
                                                            float(toks[1]))
            self.bottomDist = geomHelper.metersDistanceBetween(float(toks[2]), float(toks[3]), float(toks2[2]),
                                                               float(toks[3]))
            print("leftDist=%s; rightDist=%s; topDist=%s; bottomDist=%s\n\n\n" % (
            self.leftDist, self.rightDist, self.topDist, self.bottomDist))

            # self.leftDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks[0]), float(toks2[1]))
            # self.rightDist = geomHelper.metersDistanceBetween(float(toks[6]), float(toks[7]), float(toks[6]), float(toks2[7]))
            # self.topDist = geomHelper.metersDistanceBetween(float(toks[0]), float(toks[1]), float(toks2[0]), float(toks[1]))
            # self.bottomDist = geomHelper.metersDistanceBetween(float(toks[2]), float(toks[3]), float(toks2[2]), float(toks[3]))
            # print "leftDist=%s; rightDist=%s; topDist=%s; bottomDist=%s" % (self.leftDist, self.rightDist, self.topDist, self.bottomDist)

        # sys.exit(0)
        print("DUMP:\n%s" % self.metadata.toString())

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    # for SPOT, as in dimap_spot_product.py
    #
    def extractFootprintSpot(self, helper):
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
