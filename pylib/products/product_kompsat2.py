# -*- coding: cp1252 -*-
#
# this class represent a worldview directory product
#
#  - 
#  - 
#
#
import os
import subprocess
import zipfile
from subprocess import call

from . import browse_metadata
from . import metadata
from .browseImage import BrowseImage
#
from .product_directory import Product_Directory
from .sectionIndentedDocument import SectionDocument
from xml_nodes import rep_footprint

#


# gdal commands
GDAL_STEP_0 = 'gdal_translate -b 1 -scale 0 2048 -ot byte -outsize 25% 25% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 1 -scale 0 2048 -ot byte -outsize 25% 25% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 1 -scale 0 2048 -ot byte -outsize 25% 25% @SRC @DEST3'
GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
GDAL_STEP_4 = 'gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


class Product_Kompsat2(Product_Directory):
    #
    # metadata is text lines, name valu \t separated 
    #
    xmlMapping = {metadata.METADATA_START_DATE: 'IMG_ACQUISITION_START_TIME*|0',
                  metadata.METADATA_STOP_DATE: 'IMG_ACQUISITION_END_TIME*|0',
                  metadata.METADATA_SENSOR_NAME: 'AUX_SATELLITE_SENSOR*|0',
                  metadata.METADATA_INSTRUMENT_AZIMUTH_ANGLE: 'AUX_IMAGE_SATELLITE_AZIMUTH_DEG*|0',
                  metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'AUX_IMAGE_SATELLITE_INCIDENCE_DEG*|0',
                  metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER_NAME: 'AUX_PROJECTION_NAME*|0',
                  metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'AUX_PROJECTION_PARAMETER*|0',
                  'AUX_LOCATION_KGRS_KJ': 'AUX_LOCATION_KGRS_KJ*|0',
                  metadata.METADATA_ORBIT: 'AUX_IMAGE_ORBIT_NUMBER*|0',
                  'TL': 'AUX_IMAGE_TL_LATLONG_DEG*|0',
                  'TR': 'AUX_IMAGE_TR_LATLONG_DEG*|0',
                  'BL': 'AUX_IMAGE_BL_LATLONG_DEG*|0',
                  'BR': 'AUX_IMAGE_BR_LATLONG_DEG*|0',
                  # metadata.METADATA_FOOTPRINT:'AUX_IMAGE_TL_LATLONG_DEG*|0,1,2,3,4,5',
                  metadata.METADATA_FOOTPRINT: 'AUX_IMAGE_TL_LATLONG_DEG*|0,3,5,2,0'
                  }

    METADATA_SUFFIX_1 = 'G_1G.eph'
    METADATA_SUFFIX_2 = 'G_1R.eph'
    PREVIEW_SUFFIX = 'br.jpg'
    # G product
    TIFR_SUFFIX = 'M4N01R_1G.tif'
    TIFG_SUFFIX = 'M1N01G_1G.tif'
    TIFB_SUFFIX = 'M2N01B_1G.tif'
    # R product
    TIFRR_SUFFIX = 'M4N00R_1R.tif'
    TIFRG_SUFFIX = 'M1N00G_1R.tif'
    TIFRB_SUFFIX = 'M2N00B_1R.tif'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        # there is one browse
        # and we consider one (on 4) metadata file: ...G_1G.eph or ....G_1R.eph
        self.metContentName = None
        self.metContent = None
        self.previewContentName = None
        self.previewContent = None
        self.isG = False
        if self.debug != 0:
            print(" init class Product_Kompsat2")

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
    def runBrowseCommands(self, processInfo):
        print(" runBrowseCommands")
        processInfo.addLog("    runBrowseCommands")
        #
        print("prepareBrowseCommands: src=%s; dest=%s" % (self.jpegPath, self.browseDestPath))

        # extract 3 band, equialize
        destPathBase = self.browseDestPath.replace('.PNG', '_')
        command = GDAL_STEP_0.replace('@SRC', "%s/%s" % (processInfo.workFolder, self.TIFR))
        command1 = command.replace('@DEST1', "%s_R.tif" % destPathBase)

        command2 = GDAL_STEP_1.replace('@SRC', "%s/%s" % (processInfo.workFolder, self.TIFG))
        command2 = command2.replace('@DEST2', "%s_G.tif" % destPathBase)

        command3 = GDAL_STEP_2.replace('@SRC', "%s/%s" % (processInfo.workFolder, self.TIFB))
        command3 = command3.replace('@DEST3', "%s_B.tif" % destPathBase)

        command4 = GDAL_STEP_3.replace('@DEST1', "%s_R.tif" % destPathBase).replace('@DEST2',
                                                                                    "%s_G.tif" % destPathBase).replace(
            '@DEST3', "%s_B.tif" % destPathBase)
        command4 = command4.replace('@DEST4', "%s_bmerged.tif" % destPathBase)

        command5 = "%s -transparent %s %s 0xff000000" % (
        self.stretcherAppExe, "%s_bmerged.tif" % destPathBase, "%s_transparent.tif" % destPathBase)

        command6 = "%s -stretch %s %s 0.01" % (
        self.stretcherAppExe, "%s_transparent.tif" % destPathBase, "%s_transparent_stretched.tif" % destPathBase)

        command7 = "%s -autoBrighten %s %s 85" % (
        self.stretcherAppExe, "%s_transparent_stretched.tif" % destPathBase, self.browseDestPath)

        commands = "%s%s%s%s%s%s%s" % (
        writeShellCommand(command1, True), writeShellCommand(command2, True), writeShellCommand(command3, True),
        writeShellCommand(command4, True), writeShellCommand(command5, True), writeShellCommand(command6, True),
        writeShellCommand(command7, True))

        commands = "%s\necho\necho\necho 'browse 2 done'" % commands

        #
        commandFile = "%s/command_browse.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        # command="/bin/sh -f %s" % (commandFile)
        # launch the main make_browse script:
        command = "/bin/bash -i -f %s/command_browse.sh >%s/command_browse.stdout 2>&1" % (
        processInfo.workFolder, processInfo.workFolder)
        # 
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            print("Error generating browse, exit coded:%s" % retval)
            aStdout = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            print("Error generating browse, stdout:" % aStdout)
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

    #
    #
    #
    def makeBrowses(self, processInfo):
        if self.debug != 0:
            print(" makeBrowses")
        processInfo.addLog(" makeBrowses")
        anEosip = processInfo.destProduct
        # browse path 
        browseRelPath = os.path.dirname(anEosip.folder)
        # the extracted jpg
        self.jpegPath = "%s/%s" % (browseRelPath, self.previewContentName)

        #
        browseName = processInfo.destProduct.getSipProductName()
        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)
        # pngPath = "%s/%s" % (processInfo.workFolder, os.path.basename(jpegPath).replace('.jpg','.PNG'))

        # print "@@@@@@@@@@@ convert jpg:%s into png:%s" % (jpegPath, browseDestPath)
        # imageUtil.makeBrowse('PNG', jpegPath, browseDestPath)

        # use external command
        self.runBrowseCommands(processInfo)

        self.previewContentName = self.browseDestPath
        anEosip.addSourceBrowse(self.browseDestPath, [])

        # create browse choice for browse metadata report
        bmet = anEosip.browse_metadata_dict[self.browseDestPath]
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

        processInfo.addLog("  browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

        # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
        # if specified in configuration
        tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

        # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
        tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

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
        self.isKompsat = False
        for name in z.namelist():
            n = n + 1
            if self.debug != 0:
                print("  extract[%d]:%s" % (n, name))

            band = None
            shortName = os.path.basename(name)
            if shortName.endswith('.tif'):
                if len(shortName) == 44:
                    band = shortName[31:33]
                    print("  ##################### band=%s; on name:%s" % (band, shortName))
                else:
                    print("  ##################### not length 44 on name:%s; but:%s" % (shortName, len(shortName)))

            # keep metadata and preview data
            if name.endswith(self.METADATA_SUFFIX_1):  # metadata 1
                self.isG = True
                self.metContentName = name
                if self.debug != 0:
                    print("   metContentName 1:%s" % name)
                data = z.read(name)
                self.metContent = data
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
            elif name.endswith(self.METADATA_SUFFIX_2):  # metadata 2
                self.metContentName = name
                if self.debug != 0:
                    print("   metContentName 2:%s" % name)
                data = z.read(name)
                self.metContent = data
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
            elif name.endswith(self.PREVIEW_SUFFIX):  # preview
                self.previewContentName = name
                if self.debug != 0:
                    print("   previewContentName:%s" % self.previewContentName)
                data = z.read(name)
                self.previewContent = data
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            # keep r g b tif src files path
            # TIFR_SUFFIX='M4N01R_1G.tif'
            # TIFG_SUFFIX='M1N01R_1G.tif'
            # TIFB_SUFFIX='M2N01R_1G.tif'
            elif band == 'M4':  # name.endswith(self.TIFR_SUFFIX): #
                self.TIFR = name
                if self.debug != 0:
                    print("   TIFR:%s" % self.TIFR)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            elif band == 'M1':  # name.endswith(self.TIFG_SUFFIX): #
                self.TIFG = name
                if self.debug != 0:
                    print("   TIFG:%s" % self.TIFG)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            elif band == 'M2':  # name.endswith(self.TIFB_SUFFIX): #
                self.TIFB = name
                if self.debug != 0:
                    print("   TIFB:%s" % self.TIFB)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()


            elif band == 'M4':  # name.endswith(self.TIFRR_SUFFIX): #
                self.TIFR = name
                if self.debug != 0:
                    print("   TIFR:%s" % self.TIFR)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            elif band == 'M1':  # name.endswith(self.TIFRG_SUFFIX): #
                self.TIFG = name
                if self.debug != 0:
                    print("   TIFG:%s" % self.TIFG)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            elif band == 'M2':  # name.endswith(self.TIFRB_SUFFIX): #
                self.TIFB = name
                if self.debug != 0:
                    print("   TIFB:%s" % self.TIFB)
                data = z.read(name)
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    # print "   parent:%s" % (parent)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

        z.close()
        fh.close()
        # os._exit(1)

        if self.metContent is None:
            raise Exception("No metadata file found in this product")

    #
    #
    #
    def buildTypeCode(self):
        if self.isG:
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, "MSC_MUL_1G")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, "MSC_MUL_1R")

    #
    #
    #
    def extractMetadata(self, met=None):

        # set some evident values
        met.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.origName)

        # use what contains the metadata file
        metContent = self.getMetadataInfo()

        # extact metadata, not xml data but 'text section indented'
        sectionDoc = SectionDocument()
        # sectionDoc.DEBUG=1
        sectionDoc.setContent(self.metContent)

        # get fields
        num_added = 0
        self.debug = 1

        for field in self.xmlMapping:
            rule = self.xmlMapping[field]
            aValue = None
            if self.debug != 0:
                print(" ##### handle metadata:%s" % field)

            toks = rule.split('|')
            if len(toks) != 2:
                raise Exception("malformed metadata rule:%s" % field)
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
                    aValue = "%s%s" % (aValue, sectionDoc.getLineValue(nLine, separator='\t'))
                if self.debug != 0:
                    print("  metadata:%s='%s'" % (field, aValue))
            else:
                aValue = sectionDoc.getValue(toks[0], toks[1])
            # supress initial space is any
            if aValue[0] == ' ':
                aValue = aValue[1:]
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        met.addLocalAttribute("originalName", self.origName)

        self.metadata = met

        # refine
        self.refineMetadata(None)

        self.buildTypeCode()

    #
    # refine the metada
    #
    def refineMetadata(self, helper):
        # footprint
        # strip it, set only one space between coords
        tmp1 = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT).strip()
        tmp = tmp1.replace('\r', ' ')
        toks = tmp.split(' ')
        res = ''
        for item in toks:
            if len(item.strip()) > 0:
                if len(res) > 0:
                    res = "%s " % res
                res = "%s%s" % (res, item)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, res)
        print(" footprint changed from: to:\n%s\n%s" % (tmp1, res))

        # start stop date are like: 2008 10 06 08 28 51.222969
        # keep up to msec 3 digits
        # start
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        toks = tmp.split(' ')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, "%s-%s-%s" % (toks[0], toks[1], toks[2]))
        if toks[5].find('.') > 0:
            toks[5] = toks[5][0:toks[5].find('.') + 4]
        else:
            raise Exception("invalid start time: no msec?:%s" % toks[5])

        # only one digit for second?
        if toks[5].find('.') == 1:
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, "%s:%s:0%s" % (toks[3], toks[4], toks[5]))
        elif toks[5].find('.') == 2:
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, "%s:%s:%s" % (toks[3], toks[4], toks[5]))
        else:
            raise Exception("strange second format:'%s'" % toks[5])

        # stop
        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        toks = tmp.split(' ')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, "%s-%s-%s" % (toks[0], toks[1], toks[2]))
        if toks[5].find('.') > 0:
            toks[5] = toks[5][0:toks[5].find('.') + 4]
        else:
            raise Exception("invalid stop time: no msec?:%s" % toks[5])

        # only one digit for second?
        if toks[5].find('.') == 1:
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, "%s:%s:0%s" % (toks[3], toks[4], toks[5]))
        elif toks[5].find('.') == 2:
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, "%s:%s:%s" % (toks[3], toks[4], toks[5]))
        else:
            raise Exception("strange second format:'%s'" % toks[5])

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # track frame from filename: pppp path, rrrr row
        # MSC_YYMMDDHhmmss_nnnnn_PPPPrrrrPAxx_tt.tif
        toks = self.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME).split('_')
        path = toks[3][0:4]
        row = toks[3][4:8]
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, path)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, row)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, path)
        self.metadata.setMetadataPair(metadata.METADATA_FRAME, row)

        # DUMMY VALUES
        # self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION, "0001") # in the sip package name
        # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, "000") # in the MD

        #
        self.extractFootprint(helper)

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper):
        # the footprint in Ikonos are not starting all on the same corner. Get top left footprint
        # calculate boundingbox and scene center
        browseIm = BrowseImage()
        browseIm.setFootprint(self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        lat, lon = browseIm.calculateCenter()
        #
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lat, lon))
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, lat)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, lon)
        # boundingBox is needed in the localAttributes
        # browseIm.calculateBoondingBox()
        # met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        # met.addLocalAttribute("boundingBox", met.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

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
