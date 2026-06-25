# -*- coding: cp1252 -*-
#
# this class represent a skysat directory product
# 
# Supported types
"""
� CSG_AN4_1B: Level 1B 4-bands Analytic /DN Basic scene
� CSG_PAN_1B: Level 1B 1-bands Panchromatic /DN Basic scene  <== was corrected from 4 bands to 1 band in received email
� CSG_PAN_1A: Level 1A 1-band Panchromatic DN Pre Sup resolution Basic scene
� CSG_VIS_3B: Level 3B 3-bands Visual Ortho Scene
� CSG_PS4_3B: Level 3B 4-bands Pansharpened Multispectral Ortho Scene
� CSG_AN4_3B: Level 3B 4-bands Analytic/DN Ortho Scene
� CSG_PAN_3B: Level 3B 1-band Panchromatic /DN Ortho Scene
"""
import json
#
import os
import shutil

from . import browse_metadata
#
import eoSip_converter.imageUtil as imageUtil
from . import formatUtils
from . import metadata
from . import product_EOSIP
from .browseImage import BrowseImage
# from product import Product
from .product_directory import Product_Directory
from xml_nodes import rep_footprint

# for verification
REF_TYPECODE = {'CSG_AN4_1B',
                'CSG_PAN_1B',
                'CSG_PAN_1A',
                'CSG_VIS_3B',
                'CSG_PS4_3B',
                'CSG_AN4_3B',
                'CSG_PAN_3B'}

WITH_BOUNDINGBOX = ['CSG_VIS_3B',
                    'CSG_PS4_3B',
                    'CSG_AN4_3B',
                    'CSG_PAN_3B']

BROWSE_SUFFIX = "_visual.tif"

GSD = 'gsd'


class Product_Skysat(Product_Directory):
    jsonMapping = {
        metadata.METADATA_START_DATE_TIME: "['properties']['acquired']",
        metadata.METADATA_SUN_ELEVATION: "['properties']['sun_elevation']",
        metadata.METADATA_SUN_AZIMUTH: "['properties']['sun_azimuth']",
        metadata.METADATA_CLOUD_COVERAGE: "['properties']['cloud_cover']",
        metadata.METADATA_FOOTPRINT: "['geometry']['coordinates']",
        metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: "['properties']['view_angle']",
        metadata.METADATA_RESOLUTION: "['properties']['pixel_resolution']",
        GSD: "['properties']['gsd']"
    }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        self.metadata_path = path
        fd = open(path, 'r')
        self.metadata_content = json.load(fd)
        fd.close()

        #
        self.preview_path = None

        #
        self.useBbox = False

        #
        self.supResolution = None

        #
        self.productFolderName = os.path.basename(os.path.dirname(self.path))

        self.EO_FOLDER = os.path.dirname(path)

        if self.debug != 0:
            print(" init class Skysat")

    #
    # read matadata file
    #
    def getMetadataInfo(self, index=0):
        pass

    #
    #
    #
    def makeBrowses(self, processInfo):
        if self.preview_path is None:
            raise Exception("No visual .tif found")

        anEosip = processInfo.destProduct

        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)

        resize = True
        ratio = 1
        w, h = imageUtil.get_image_size(self.preview_path)
        if w == 1 or h == 1:
            resize = False
        if resize and w < 1600 and h < 1600:
            resize = False
        if resize:
            maxd = w if w > h else h
            ratio = 1600.0 / maxd
        print((" source .tif size: w=%s h=%s; resize:%s, ratio=%s" % (w, h, resize, ratio)))
        imageUtil.makeBrowse("PNG", self.preview_path, self.browseDestPath, resizePercent=ratio * 100.0,
                             transparent=True)

        # set AM time if needed
        anEosip.setFileAMtime(self.browseDestPath)
        processInfo.destProduct.addSourceBrowse(self.browseDestPath, [])
        processInfo.addLog(" browse image added: name=%s; path=%s" % (browseName, self.browseDestPath))

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
            print("browseChoiceBlock :%s" % browseChoiceBlock)
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

        processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

    #
    # extract the spot 6 7 interresting piece in working folder:
    # - metadata xml
    # - preview images
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

        # keep list of content
        self.contentList = []
        #
        self.num_preview = 0
        #
        n = 0
        for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):
            for name in files:
                n = n + 1
                eoFile = "%s/%s" % (root, name)
                print(" ## product content[%d]:'%s' in:%s" % (n, name, eoFile))

                if name.lower().endswith(BROWSE_SUFFIX):
                    self.preview_path = eoFile
                    shutil.copyfile(self.preview_path, "%s/%s" % (folder, name))
                    print((" ## FOUND self.preview_path=%s" % self.preview_path))

    #
    #
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met == None:
            raise Exception("metadate is None")

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        # save metadata to workfolder for test purpose:
        destPath = "%s/%s" % (processInfo.workFolder, os.path.basename(self.path))
        shutil.copyfile(self.path, destPath)

        numAdded = 0
        jsonMetadata = self.metadata_content
        for key in self.jsonMapping:
            mapping = self.jsonMapping[key]
            try:
                print((" extracted metadata '%s' using mapping: '%s'" % (key, mapping)))
                value = eval("self.metadata_content%s" % mapping)
                print(("  extracted metadata '%s' value: '%s'" % (key, value)))
                met.setMetadataPair(key, value)
                numAdded == 1
            except:
                print((" !! metadata not found: '%s' using mapping: '%s'" % (key, mapping)))

        self.metadata = met

        #
        self.refineMetadata(processInfo)

        #
        self.extractFootprint(processInfo)

        #
        self.buildTypeCode(processInfo)

        # set local attribute for the one with boundingbox
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        if tmp in WITH_BOUNDINGBOX:
            processInfo.addLog("## have boundingBox:%s" % tmp)
            self.metadata.addLocalAttribute("boundingBox", self.browseIm.getBoundingBox())

            """
            OrthoSceneType Allowed types:
            - Visual Ortho
            - Pansharpened Multispectral
            - Analytic DN Ortho
            - Panchromatic DN Ortho
            - Analytic Ortho
            """
            self.metadata.addLocalAttribute("OrthoSceneType", "OrthoSceneType")
        else:
            processInfo.addLog("## have NO boundingBox:%s" % tmp)

    #
    # refine the metada
    #
    def refineMetadata(self, processInfo):
        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        #
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        # print("#### start:"+start)
        # os._exit(1)
        pos = start.find('.')
        msec = ".000"
        if pos > 0:
            start = start[0:pos + 4] + "Z"
            msec = "." + start[pos + 1: pos + 4]
        else:
            posZ = start.find('Z')
            start = start[:posZ] + msec + start[posZ]

        print(("## START:%s" % start))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start.split("T")[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start.split("T")[1].split('.')[0] + msec)

        #
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, start)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, start.split("T")[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, start.split("T")[1].split('.')[0] + msec)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # addLocalAttribute
        self.metadata.addLocalAttribute("originalName", self.productFolderName)

        # gsd < 0.8: Sup Resolution
        gsd = self.metadata.getMetadataValue(GSD)
        if gsd < 0.8:
            print("######## product is Sup Resolution")
            self.supResolution = True
        else:
            print("######## product is NOT Sup Resolution")
            self.supResolution = False

    def buildTypeCode(self, processInfo):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, 'CSG_AN4_1B')

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, processInfo):

        # keep a copy
        self.metadata.setMetadataPair("json-footprint",
                                      "%s" % self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        tmp = self.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT)  # is a list because we get what is parsed: json. So we get str/int/float...
        # print("FOOTPRINT 0:%s type:%s"  % (tmp, type(tmp)))
        footprint = "%s %s %s %s %s %s %s %s %s %s" % (tmp[0][2][0], tmp[0][2][1],
                                                       tmp[0][1][0], tmp[0][1][1],
                                                       tmp[0][0][0], tmp[0][0][1],
                                                       tmp[0][3][0], tmp[0][3][1],
                                                       tmp[0][2][0], tmp[0][2][1],
                                                       )
        self.metadata.setMetadataPair("first-footprint", footprint)
        # print("FOOTPRINT: %s"  % footprint)
        # os._exit(1)

        # get center
        # make sure the footprint is CCW
        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        if self.debug != 0:
            print("browseIm:%s" % browseIm.info())
        if not browseIm.getIsCCW():
            # reverse
            if self.debug != 0:
                print("############### reverse the footprint; before:%s" % footprint)
            browseIm.reverseFootprint()
            if self.debug != 0:
                print("###############             after;%s" % (browseIm.getFootprint()))
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        flat, flon = browseIm.calculateCenter()
        flat = float(flat)
        flon = float(flon)

        #
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))

        #
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
