# -*- coding: cp1252 -*-
#
# this class represent an irs1c-1d product
#
#  - 
#  - 
#
#
import math
import os
import re
import shutil
import subprocess

from osgeo import gdal
# gdal projection transformation
from osgeo import ogr
from osgeo import osr

from . import browse_metadata
import eoSip_converter.fileHelper as fileHelper
import eoSip_converter.geomHelper as geomHelper
#
# import eoSip_converter.xmlHelper as xmlHelper
import eoSip_converter.imageUtil as imageUtil
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
# from product import Product
from .product_directory import Product_Directory
from xml_nodes import rep_footprint
from xml_nodes import sipBuilder

# import eoSip_converter.fileHelper


BROWSE_SIZE = 800


#
#
#
def twoDigitsYearToFourdigits(s):
    try:
        int(s)
    except:
        raise Exception("can not get 4digit year from 2 digit:%s" % s)
    year = None
    if int(s[0]) > 5:
        year = '19%s' % s
    else:
        year = '20%s' % s
    if year is None:
        raise Exception("can not get 4digit year from 2 digit:%s" % s)
    return year


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
    point.AddPoint(lon, lat)  # Berlin lon, lat
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


class Product_Irs1c_1d(Product_Directory):
    # for IRS

    irsInfos = ['INF_Subscene_no', 'INF_Quadrant_no', 'INF_AWiFS_Subscene', 'INF_Shift']
    #
    irsMapping = {'image_width': '102 1281 1296 I16',
                  'image_height': '103 1297 1312 I16',
                  'MISSION': ' 58  830  845 A16  ',
                  metadata.METADATA_PLATFORM: ' 58  830  845 A16  ',
                  metadata.METADATA_INSTRUMENT: ' 59  846  877 A32  ',
                  metadata.METADATA_ORBIT: ' 47  518  525    ',
                  metadata.METADATA_TRACK: '  6   21   28 I8   ',
                  metadata.METADATA_FRAME: '  7   29   36 I8   ',
                  'processing_date': '  7   33   48 A16  ',
                  'processing_time': '  8   49   64 A16  ',
                  metadata.METADATA_SUN_AZIMUTH: ' 50  574  589 F16.7',
                  metadata.METADATA_SUN_ELEVATION: ' 51  590  605 F16.7',
                  'SCENE_ID': ' 10   81  112 A32  ',
                  'CLAT': ' 10  101  116 F16.7',
                  'CLONG': ' 11  117  132 F16.7',
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

    #
    METADATA_TXT = '_ssd.txt'
    INFO_TXT = '_inf.txt'
    IMAGE = '_pan.tif'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_Image2006IrsP6")
        self.metadataName_txt = None
        self.metadataContent_txt = None
        self.infoSrcPath = None
        self.infoContent_txt = None
        self.imageSrcPath = None
        self.imageWorkPath = None
        #
        self.basePathProduct = None

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
        srcPath = self.imageWorkPath
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
        command = 'echo "CWD:`pwd`"'
        command = '%s\necho "PATH=$PATH"' % command
        # gdal_translate
        command = "%s\n%s" % (command, writeShellCommand(
            "gdal_translate -outsize %s %s -of png %s %s" % (ratios, ratios, srcPath, self.browseDestPath), 1))

        commandFile = "%s/command_browse.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(command)
        fd.close()
        # os.chmod(commandFile, 0755)
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
        # command="/bin/bash -f %s/command_browse.sh" % (processInfo.workFolder)
        command = "/bin/bash -i -f %s/command_browse.sh >%s/command_browse.stdout 2>&1" % (
        processInfo.workFolder, processInfo.workFolder)
        # commandList = command.split(" ")
        # 
        retval = subprocess.call(command, shell=True)
        # retval = subprocess.call(commandList, shell=False)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            print("Error generating browse, exit coded:%s" % retval)
            # aStdout = subprocess.check_output(commandList, shell=False)
            aStdout = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            print("Error generating browse, stdout:" % aStdout)
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        # crop util pixels for IRSP6
        # if not self.isSpot or 1==1:
        if 2 == 1:
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

        # set AM time if needed
        processInfo.destProduct.setFileAMtime(self.browseDestPath)

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

        # source is the .sd file that is inside the ~/EM_TIFF_Kit_1/ folder
        self.basePathProduct = os.path.dirname(os.path.dirname(self.path))
        if self.debug != 0:
            print("  basePathProduct:%s " % self.basePathProduct)
        aFileHelper = fileHelper.FileHelper()
        reNamePattern = re.compile(".*")
        self.contentList = aFileHelper.list_files(self.basePathProduct, reNamePattern, None)

        #
        basePath = "/" + os.path.dirname(self.basePathProduct).replace('\\', '/')
        if self.debug != 0:
            print("  basePath:%s" % basePath)
        # os._exit(-1)

        #
        n = 0
        self.additionalContent = {}
        self.relBasePaths = {}
        for name in self.contentList:
            n = n + 1
            # if self.DEBUG!=0:
            #    print "  product file[%d]:%s" % (n, name)

            # get manifest filename and data
            if name.endswith(self.METADATA_TXT):
                if self.debug != 0:
                    print("   metadata found:%s" % name)
                self.metadataName_txt = name
                # basePath = '/'+os.path.join(*name.split('/')[0:-2]).replace('\\','/')
                # print "   metadata basePath:%s" % (basePath,)
                relBasePath = name[len(basePath) + 1:]
                if self.debug != 0:
                    print("   metadata relPath:%s" % (relBasePath,))
                tmp = "%s/%s" % (folder, os.path.dirname(relBasePath))
                if not os.path.exists(tmp):
                    os.makedirs(tmp)
                shutil.copyfile(name, "%s/%s" % (folder, relBasePath))
                fd = open(name, 'r')
                self.metadataContent_txt = fd.read()
                fd.close()
                #

            elif name.endswith(self.INFO_TXT):
                if self.debug != 0:
                    print("   info found:%s" % name)
                self.infoSrcPath = name
                fd = open(name, 'r')
                self.infoContent_txt = fd.read()
                fd.close()

            elif name.endswith(self.IMAGE):
                if self.debug != 0:
                    print("   image found:%s" % name)
                self.imageSrcPath = name
                # basePath = '/'+os.path.join(*name.split('/')[0:-2]).replace('\\','/')
                if self.debug != 0:
                    print("   image basePath:%s" % (basePath,))
                relBasePath = name[len(basePath) + 1:]
                if self.debug != 0:
                    print("   image relPath:%s" % (relBasePath,))
                tmp = "%s/%s" % (folder, os.path.dirname(relBasePath))
                if not os.path.exists(tmp):
                    os.makedirs(tmp)
                self.imageWorkPath = "%s/%s" % (folder, relBasePath)
                shutil.copyfile(name, self.imageWorkPath)

            else:
                # basePath = '/'+os.path.join(*name.split('/')[0:-2]).replace('\\','/')
                if self.debug != 0:
                    print("   basePath:%s" % (basePath,))
                relBasePath = name[len(basePath) + 1:]

            # self.contentList=[]
            self.relBasePaths[name] = relBasePath
            print("    content[%s]:  name:%s;relBasePath:%s" % (n, name, relBasePath))

        if self.metadataName_txt is None:
            raise Exception("unknown product: metadata_txt not found")

        if self.imageSrcPath is None:
            raise Exception("unknown product: previewName not found")

        # os._exit(-1)

    #
    #
    #
    def buildTypeCode(self):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'PAN_P___1A')

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadata 0 is None")

        self.extractMetadataIrs(met)

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        #
        met.addLocalAttribute("originalName", self.origName.replace("_ssd.txt", ""))

        self.metadata = met

        # refine
        self.refineMetadata()

    #
    # extract irsp6 metadata
    #
    def extractMetadataIrs(self, met=None):
        if met == None:
            raise Exception("metadata 1 is None")

        self.metadata = met

        #
        self.getMetadataFromInfoFile()

        # use what contains the metadata file
        if self.metadataContent_txt is None:
            raise Exception("no metadata_txt to be parsed")

        lines = self.metadataContent_txt.split('\n')
        print("Irs metadata file contains:%s lines" % len(lines))

        # extact metadata
        num_added = 0
        for field in self.irsMapping:
            if self.debug != 0:
                print("  do field[%s]:%s" % (num_added, field))
            key = self.irsMapping[field]

            for line in lines:
                if line.startswith(key):
                    aValue = getIrsValueFromLine(line[len(key):])
                    print("    met[%s] -->%s or %s value:'%s'" % (num_added, field, key, aValue))
                    met.setMetadataPair(field, aValue)
                    num_added += 1
                    break

        print("  metadata num_added:%s" % num_added)

        # instrument: fixed
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'PAN')

        tmp = self.metadata.getMetadataValue('processing_date').replace('>', '').replace('<', '').replace(' ',
                                                                                                          '')  # DD-MM-YY
        tmp1 = self.metadata.getMetadataValue('processing_time').replace('>', '').replace('<', '').replace(' ', '')
        print("  processing_date:%s; processing_time:%s" % (tmp, tmp1))
        toks = tmp.split('-')
        if len(toks) == 3:
            # if int(toks[2][0]) > 5:
            #   year = '20%' % toks[2]
            # else:
            #    year = '19%s' % toks[2]
            year = twoDigitsYearToFourdigits(toks[2])
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME,
                                          "%s-%s-%sT%sZ" % (year, toks[1], toks[0], tmp1))
        else:
            raise Exception("invalid date format:'%s'" % tmp)

        clat = self.metadata.getMetadataValue('CLAT')
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, clat)
        clon = self.metadata.getMetadataValue('CLONG')
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
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
        self.metadata.setMetadataPair('utilPixelsFootprint', footprint)

        browseIm = BrowseImage()
        browseIm.setFootprint(footprint)
        # get scene center
        clat2, clon2 = browseIm.calculateCenter()
        browseIm.calculateBoondingBox()
        self.metadata.setMetadataPair('utilPixelsBoundingBox', browseIm.boondingBox)
        # self.metadata.addLocalAttribute("boundingBox", browseIm.boondingBox)
        # self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        # self.metadata.addLocalAttribute("boundingBox", self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        # software version like:IRSP6DPSV1R2
        version = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        # fileVersion = version.replace('IRS1CDPSV','')#.replace('R','')
        # 'IRS1CDPSV' is not the only possibility, so:
        fileVersion = version[9:]  #
        print("version:'%s'; fileVersion0:'%s'" % (version, fileVersion))
        if len(fileVersion) > 3:
            if fileVersion[0] == '0':
                fileVersion = fileVersion[1:]
            if fileVersion[0] == '0':
                fileVersion = fileVersion[0:3]
        elif len(fileVersion) < 3:
            fileVersion = formatUtils.leftPadString(fileVersion, 3, '0')
        print("fileVersion1:'%s'" % fileVersion)

        counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        if counter is None or counter == sipBuilder.VALUE_NOT_PRESENT or counter == sipBuilder.VALUE_NONE:  # counter==sipBuilder.VALUE_NONE:
            counter = '1'
        else:
            print("counter is present:'%s'" % counter)

        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION,
                                      "%s%s" % (fileVersion, counter))  # in the sip package name
        # self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, version.replace('IRS1CDPSV',''))
        # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version.replace('IRS1CDPSV',''))

        # if self.DEBUG!=0:
        # print " version:%s; fileVersion:%s" % (version, fileVersion)

        # set IRSP6 METADATA_PLATFORM_2DIGITS_ALIAS=WV
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, 'I1')

        if 1 == 2:
            # do xxx_inf.txt file content
            if self.infoContent_txt is not None:
                n = 0
                found = 0
                lines = self.infoContent_txt.split('\n')
                for line in lines:
                    if found == len(self.irsInfos):
                        print(" all info found")
                        break
                    line = line.strip()
                    print(" line[%s] '%s'" % (n, line))
                    if len(line) > 0 and line[0] != '#':
                        for i in range(len(self.irsInfos)):
                            print(" test info line for '%s'" % self.irsInfos[i])
                            if line.find(self.irsInfos[i]) >= 0:
                                value = line[len(self.irsInfos[i]) + 1]
                                self.metadata.setMetadataPair(self.irsInfos[i], value)
                                print("  info line%s='%s'" % (self.irsInfos[i], value))
                                found += 1
                    n += 1

            else:
                raise Exception('no xxx_inf.txt content available')
                # sys.exit(0)

        # sys.exit(0)

    #
    # extract metadata from xxx_inf.txt file
    #
    def getMetadataFromInfoFile(self):
        # do xxx_inf.txt file content
        if self.infoContent_txt is not None:
            n = 0
            found = 0
            lines = self.infoContent_txt.split('\n')
            founds = []
            for line in lines:
                if found == len(self.irsInfos):
                    print(" all info found:%s" % founds)
                    break
                line = line.strip()
                if self.debug != 0:
                    print(" line[%s] '%s'" % (n, line))
                if len(line) > 0 and line[0] != '#':
                    for i in range(len(self.irsInfos)):
                        if self.debug != 0:
                            print(" test info line for '%s'" % self.irsInfos[i])
                        if line.find(self.irsInfos[i]) >= 0:
                            value = line[len(self.irsInfos[i]) + 1:]
                            self.metadata.setMetadataPair(self.irsInfos[i], value)
                            if self.debug != 0:
                                print("  info line%s='%s'" % (self.irsInfos[i], value))
                            founds.append(value)
                            found += 1
                n += 1

        else:
            raise Exception('no xxx_inf.txt content available')
            # sys.exit(0)

        # use INF_Subscene_no if any as filecounter
        value = self.metadata.getMetadataValue('INF_Subscene_no')
        if value is not None:
            counter = value[-1]
            print("###@@@### counter from subscene:'%s' -> %s" % (value, counter))
            self.metadata.setMetadataPair(metadata.METADATA_FILECOUNTER, counter)
            self.metadata.setMetadataPair("use INF_Subscene_no as filecounter", "YES:%s" % counter)
            self.metadata.addLocalAttribute("subScene", counter)
        else:
            self.metadata.setMetadataPair("use INF_Subscene_no as filecounter", "NO")
            # sys.exit(-1)

    #
    # refine the metada
    #
    def refineMetadata(self):

        # start stop date time fromscene_id: 02-JUL-96 08:25:31P-BLST00S1   F
        tmp = self.metadata.getMetadataValue('SCENE_ID')
        print("tmp:%s" % tmp)
        toks = tmp.split(' ')
        month = formatUtils.getMonth2DigitFromMonthString(toks[0].split('-')[1])
        print("month:%s" % month)
        year = toks[0].split('-')[2]
        year4 = twoDigitsYearToFourdigits(year)
        print("year:%s; year4=%s" % (year, year4))
        day = toks[0].split('-')[0]
        time = toks[1][:8]

        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, "%s-%s-%s" % (year4, month, day))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, "%s-%s-%s" % (year4, month, day))
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, time)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, time)

        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION,
                                      "%sT%sZ" % ("%s-%s-%s" % (year4, month, day), time))

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED,
                                      self.metadata.getMetadataValue(metadata.METADATA_TRACK))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED,
                                      self.metadata.getMetadataValue(metadata.METADATA_FRAME))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        self.metadata.setMetadataPair('orig_METADATA_PLATFORM', tmp)
        mid = tmp.split('-')[1][1]
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, tmp.split('-')[0])
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, mid)
        print("platform:%s" % tmp.split('-')[0])
        print("platform id:%s" % mid)

        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'P')

        # os._exit(1)

        # startdateTime=fixedPart[16:31]
        # stoptdateTime=fixedPart[32:47]

        # self.metadata.setMetadataPair(metadata.METADATA_START_DATE, "%s-%s-%s" % (startdateTime[0:4], startdateTime[4:6], startdateTime[6:8]))
        # self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, "%s-%s-%s" % (stoptdateTime[0:4], stoptdateTime[4:6], stoptdateTime[6:8]))
        #
        # self.metadata.setMetadataPair(metadata.METADATA_START_TIME, "%s:%s:%s" % (startdateTime[9:11], startdateTime[11:13], startdateTime[13:15]))
        # self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, "%s:%s:%s" % (stoptdateTime[9:11], stoptdateTime[11:13], stoptdateTime[13:15]))
        # build timePosition from endTime + endDate
        # self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE), self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # platform sensor: IRS-P6-LISS III or SPOT 4
        # tmp = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        # self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, tmp.split('-')[0])
        # self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, tmp.split('-')[1])

        self.buildTypeCode()

        # country in local attributes
        # self.metadata.addLocalAttribute("country", self.metadata.getMetadataValue(metadata.METADATA_COUNTRY))

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

        return

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
    def extractFootprintSpot__NOT_USED(self, helper):
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
