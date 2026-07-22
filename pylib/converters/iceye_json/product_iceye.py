"""This class represent a worldview directory product

Supported types
XN_SM__SLC: Level 1 Strip SLC product
XN_SM__GRD: Level 1 Strip GRD product
XN_SL__SLC: Level 1 Spot SLC product
XN_SL__GRD: Level 1 Spot GRD product
XN_SR__GRD: Level 1 Scan GRD product
"""
import math
import os
import shutil
from typing import Optional

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import browse_metadata, formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory
from eoSip_converter import xmlHelper

from xml_nodes import rep_footprint

__version__ = '1.0.0'

# for verification
REF_TYPECODE = {'XN_SM__SLC', 'XN_SM__GRD', 'XN_SL__SLC', 'XN_SL__GRD', 'XN_SR__GRD'}
BROWSE_SUFFIX = ".png"
TIFF_SUFFIX = ".tif"
METADATA_SUFFIX = ".xml"
H5_SUFFIX = ".h5"

# constants:
LEVEL = 'level'
AQCUSITION_MODE = 'aquisition_mode'
ORBIT_DIRECTION = 'orbit_direction'
coord_first_near = 'coord_first_near'
coord_first_far = 'coord_first_far'
coord_last_near = 'coord_last_near'
coord_last_far = 'coord_last_far'
coord_center = 'coord_center'
velX = 'Orbit_State_Vectors/orbit_vector/velX'
velY = 'Orbit_State_Vectors/orbit_vector/velY'
velZ = 'Orbit_State_Vectors/orbit_vector/velZ'
azimuth_look_bandwidth = 'azimuth_look_bandwidth'
range_look_bandwidth = 'range_look_bandwidth'
total_processed_bandwidth_azimuth = 'total_processed_bandwidth_azimuth'
azimuth_looks = 'azimuth_looks'
azimuth_spacing = 'azimuth_spacing'
azimuth_ground_spacing = 'azimuth_ground_spacing'
range_spacing = 'range_spacing'
slant_range_spacing = 'slant_range_spacing'


class Product_Iceye(Product_Directory):
    xmlMapping = {
        metadata.METADATA_START_DATE_TIME: 'acquisition_start_utc',
        metadata.METADATA_STOP_DATE_TIME: 'acquisition_end_utc',
        metadata.METADATA_ORBIT: 'orbit_relative_number',
        metadata.METADATA_ORBIT_DIRECTION: 'orbit_direction',
        LEVEL: 'product_level',
        AQCUSITION_MODE: 'acquisition_mode',
        metadata.METADATA_SUN_AZIMUTH: 'satellite_look_angle',
        metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'incidence_center',
        metadata.METADATA_ANTENNA_LOOK_DIRECTION: 'look_side',
        metadata.METADATA_SCENE_CENTER: 'coord_center',
        coord_first_near: 'coord_first_near',
        coord_first_far: 'coord_first_far',
        coord_last_near: 'coord_last_near',
        coord_last_far: 'coord_last_far',
        coord_center: 'coord_center',
        metadata.METADATA_SATELLITE: 'satellite_name',
        velX: 'Orbit_State_Vectors/orbit_vector/velX',
        velY: 'Orbit_State_Vectors/orbit_vector/velY',
        velZ: 'Orbit_State_Vectors/orbit_vector/velZ',
        azimuth_look_bandwidth: 'azimuth_look_bandwidth',
        range_look_bandwidth: 'range_look_bandwidth',
        azimuth_looks: 'azimuth_looks',
        total_processed_bandwidth_azimuth: 'total_processed_bandwidth_azimuth',
        azimuth_spacing: 'azimuth_spacing',
        azimuth_ground_spacing: 'azimuth_ground_spacing',
        range_spacing: 'range_spacing',
        slant_range_spacing: 'slant_range_spacing',
        metadata.METADATA_SOFTWARE_VERSION: 'processor_version',
        metadata.METADATA_PROCESSING_TIME: 'processing_time'
    }

    def __init__(self, path=None):
        super().__init__(path)
        self.metadata_path = path
        with open(path, 'r') as fd:
            self.metadata_content = fd.read()

        self.preview_path = None
        self.tif_path = None
        self.productFolderName = os.path.basename(os.path.dirname(self.path))
        self.EO_FOLDER = os.path.dirname(path)
        self.tmpLevel = self.checkLevelOnTheFly(path)

        if self.debug != 0:
            print(" init class Product_iceye")

    # Called at the end of the doOneProduct, before the index/shopcart creation
    def afterProductDone(self):
        pass

    # Read matadata file
    def getMetadataInfo(self):
        pass

    def makeBrowses(self, processInfo):
        import eoSip_converter.imageUtil as imageUtil
        anEosip = processInfo.destProduct

        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)

        if self.preview_path is not None:
            imageUtil.makeBrowse("PNG", self.preview_path, self.browseDestPath, transparent=True)
        else:
            import ast
            from osgeo import gdal

            imageUtil.makeBrowse_v2(
                "PNG", self.tif_path, self.browseDestPath, transparent=True, h=4096, w=4096
            )

            # .tif can be of any orientation considering flight direction and
            # look side, therefore may need to invert resultant image in x
            # and/or y to ensure the top-left image corner is always the most
            # North-Westerly
            tif_metadata = gdal.Open(self.tif_path, gdal.GA_ReadOnly).GetMetadata()

            tif_corners = ('COORD_FIRST_FAR', 'COORD_FIRST_NEAR', 'COORD_LAST_FAR', 'COORD_LAST_NEAR')

            desired_corners = {
                'ASCENDING': {
                    'ul': 'COORD_LAST_NEAR', 'ur': 'COORD_LAST_FAR', 'lr': 'COORD_FIRST_FAR', 'll': 'COORD_FIRST_NEAR'
                },
                'DESCENDING': {
                    'ul': 'COORD_FIRST_FAR', 'ur': 'COORD_FIRST_NEAR', 'lr': 'COORD_LAST_NEAR', 'll': 'COORD_LAST_FAR'
                },
            }[tif_metadata['ORBIT_DIRECTION'].upper()]

            # Reverse the desired corners left/right if capturing towards left side
            if tif_metadata['LOOK_SIDE'].upper() == 'LEFT':
                desired_corners['ul'], desired_corners['ur'] = desired_corners['ur'], desired_corners['ul']
                desired_corners['ll'], desired_corners['lr'] = desired_corners['lr'], desired_corners['ll']

            # Values of .tif metadata always interpreted as strings
            # (hence ast.literal_eval)
            tif_current_orientation = {k: ast.literal_eval(tif_metadata[k]) for k in tif_corners}
            invert_x = tif_current_orientation[desired_corners['ul']][0] != 1
            invert_y = tif_current_orientation[desired_corners['ul']][1] != 1

            if invert_x or invert_y:
                from PIL import Image

                img = Image.open(self.browseDestPath)
                if invert_x:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                if invert_y:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                img.save(self.browseDestPath)

        # set AM time if needed
        anEosip.setFileAMtime(self.browseDestPath)
        processInfo.destProduct.addSourceBrowse(self.browseDestPath, [])
        processInfo.addLog(" browse image for L2 added: name=%s; path=%s" % (browseName, self.browseDestPath))

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
            print("browseChoiceBlock :%s" % (browseChoiceBlock))
        bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

        # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
        # if specified in configuration
        tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
        if tmp is not None:
            bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

        # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
        if tmp is not None:
            bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

        processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % (browseChoiceBlock))

    # extract the product
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        if self.debug != 0:
            print("###################### will extract directory product '%s' to path: %s" % (self.path, folder))

        print("###################### will extract directory product '%s' to path: %s" % (self.path, folder))

        self.EXTRACTED_PATH = folder

        # keep list of content
        self.contentList = []
        self.num_preview = 0
        self.tmpSize = 0
        n = 0
        for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):

            for name in files:

                n = n + 1
                eoFile = "%s/%s" % (root, name)
                print(" ## product content[%d]:'%s' in:%s" % (n, name, eoFile))
                self.tmpSize += os.stat(eoFile).st_size

                if name.lower().endswith(BROWSE_SUFFIX):
                    self.preview_path = eoFile
                    shutil.copyfile(self.preview_path, "%s/%s" % (folder, name))
                    print((" ## FOUND self.preview_path=%s" % self.preview_path))

                elif name.lower().endswith(TIFF_SUFFIX):
                    self.tif_path = eoFile
                    shutil.copyfile(self.tif_path, "%s/%s" % (folder, name))
                    print((" ## FOUND self.preview_path=%s" % self.preview_path))

        print((" ####              self.tmpLevel:%s" % self.tmpLevel))

        # SP: ESA directive May 2025
        if self.preview_path is None:
            raise FileNotFoundError(
                f"Corrupt Iceye native product (no quicklook image with '{BROWSE_SUFFIX}' suffix present)"
            )

        print((" #### extract done; preview:%s" % (self.preview_path)))

    def checkLevelOnTheFly(self, aPath):
        aValue = None
        fd = open(aPath, 'r')
        metContent = fd.read()
        fd.close()
        helper = xmlHelper.XmlHelper()
        helper.setData(metContent)
        helper.parseData()
        aData = helper.getFirstNodeByPath(None, self.xmlMapping[LEVEL], None)
        if aData is not None:
            aValue = helper.getNodeText(aData)
        return aValue

    def buildTypeCode(self, processInfo):
        level = self.metadata.getMetadataValue(LEVEL)
        sensor_mode = self.metadata.getMetadataValue(AQCUSITION_MODE)
        typecode = None
        print(("LEVEL: %s" % level))
        print(("Acquisition Mode: %s" % sensor_mode))
        # os._exit(1)

        # if mode is strip, its level can be SLC or GRD
        if sensor_mode == 'stripmap':
            sensor_mode = 'Strip'
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensor_mode)
            if level == 'SLC':
                typecode = 'XN_SM__SLC'
            elif level == 'GRD':
                typecode = 'XN_SM__GRD'
            else:
                raise Exception("unknown level: %s" % level)

        # if mode is spot, its level can be SLC or GRD
        elif sensor_mode == 'spotlight':
            sensor_mode = 'Spot'
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensor_mode)
            if level == 'SLC':
                typecode = 'XN_SL__SLC'
            elif level == 'GRD':
                typecode = 'XN_SL__GRD'
            else:
                raise Exception("unknown level: %s" % level)

        # if mode is scan, its level can only be GRD
        elif sensor_mode == 'scan':
            sensor_mode = sensor_mode.capitalize()
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensor_mode)
            if level == 'GRD':
                typecode = 'XN_SR__GRD'
            else:
                raise Exception("unknown level: %s" % level)
        else:
            raise Exception("unknown operational sensor mode: %s" % sensor_mode)

        if not typecode in REF_TYPECODE:
            raise Exception("buildTypeCode; unknown typecode:'%s'" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        print(("TYPECODE SET TO: %s" % typecode))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        # save metadata to workfolder for test purpose:
        destPath = "%s/%s" % (processInfo.workFolder, os.path.basename(self.path))
        shutil.copyfile(self.path, destPath)

        # extract metadata
        helper = xmlHelper.XmlHelper()
        helper.setData(self.metadata_content)
        helper.parseData()

        num_added = 0
        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData is None:
                aValue = None
            else:
                if attr is None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  -->%s=%s" % (field, aValue))
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        print(("metadata extracted: %s" % num_added))

        self.metadata = met
        self.buildTypeCode(processInfo)
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    # refine the metada
    def refineMetadata(self, processInfo):
        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
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
        stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME)
        pos = stop.find('.')
        msec = ".000"
        if pos > 0:
            stop = stop[0:pos + 4] + "Z"
            msec = "." + stop[pos + 1: pos + 4]
        else:
            raise Exception("unexpected stop datetime format: no .: '%s'" % stop)
        print(("## STOP:%s" % stop))

        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split("T")[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split("T")[1].split('.')[0] + msec)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(
            metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
                self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
                self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)
            )
        )

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
        if tmp is None:
            raise Exception("Incidence Angle is None")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, tmp)
            print(("## Incidence Angle: %s" % tmp))

        # orbit number
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        if tmp is None:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, 0)
        else:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, tmp)

        print(("## Orbit number: %s" % tmp))

        # orbit direction
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        print(("## Orbit Direction:%s" % tmp))
        if tmp == "ASCENDING" or tmp == "DESCENDING":
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, tmp)
        else:
            raise Exception("invalid orbit direction: %s" % tmp)

        # look direction
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ANTENNA_LOOK_DIRECTION)
        tmp = tmp.upper()

        if tmp == "RIGHT" or tmp == "LEFT":
            self.metadata.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, tmp)
        else:
            raise Exception("invalid antenna look direction: %s" % tmp)

        print(("## Antenna Look Direction: %s" % tmp))

        # center coordinates
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        tmp = tmp.split(' ')
        flat, flon = tmp[2], tmp[3]
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))

        # addLocalAttributes
        # find subclass
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        subClass = None
        print(("type code = %s" % tmp))
        if tmp == 'XN_SM__SLC' or tmp == 'XN_SL__SLC':
            subClass = 'SLC'
        elif tmp == 'XN_SM__GRD' or tmp == 'XN_SL__GRD' or tmp == 'XN_SR__GRD':
            subClass = 'GRD'
        else:
            raise Exception("invalid subClass: %s" % tmp)

        # add 'Z' to processingDate/Time
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        tmp = tmp + 'Z'
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        # find processor version
        # self.metadata.addLocalAttribute("processorVersion", self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION))

        self.metadata.addLocalAttribute("subClass", subClass)
        print(("subClass = %s" % subClass))

        # find satellite number
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SATELLITE)
        satelliteNumber = None
        if tmp is not None:
            tmp = tmp.split('-')
            tmp = tmp[1]
            satelliteNumber = tmp
            print(("tmp[1]: %s" % satelliteNumber))
            self.metadata.setMetadataPair(metadata.METADATA_SATELLITE, satelliteNumber)
        else:
            raise Exception("invalid satellite number: %s" % tmp)

        self.metadata.addLocalAttribute("satelliteNumber", satelliteNumber)
        print(("## Satellite Number: %s" % satelliteNumber))

        # find azimuth resolution + range resolution

        # first for GRD products
        if self.tmpLevel == "GRD":
            # get azimuth resolution
            tmp = float(self.metadata.getMetadataValue(azimuth_spacing))
            if tmp <= 0:
                raise Exception("invalid azimuth resolution: %s" % tmp)
            else:
                tmp = round(tmp, 1)
                self.metadata.addLocalAttribute("azimuthResolution", tmp)
                print(("## Azimuth Resolution: %s m/s" % tmp))
            # get range resolution
            tmp = float(self.metadata.getMetadataValue(range_spacing))
            if tmp <= 0:
                raise Exception("invalid range resolution: %s" % tmp)
            else:
                tmp = round(tmp, 1)
                self.metadata.addLocalAttribute("rangeResolution", tmp)
                print(("## Range Resolution: %s m/s" % tmp))
        # second for SLC products
        elif self.tmpLevel == "SLC":
            # get azimuth resolution
            tmp = float(self.metadata.getMetadataValue(azimuth_ground_spacing))
            if tmp <= 0:
                raise Exception("invalid azimuth resolution: %s" % tmp)
            else:
                tmp = round(tmp, 1)
                self.metadata.addLocalAttribute("azimuthResolution", tmp)
                print(("## Azimuth Resolution: %s m/s" % tmp))
            # get range resolution
            tmp = float(self.metadata.getMetadataValue(slant_range_spacing))
            if tmp <= 0:
                raise Exception("invalid range resolution: %s" % tmp)
            else:
                tmp = round(tmp, 1)
                self.metadata.addLocalAttribute("rangeResolution", tmp)
                print(("## Range Resolution: %s m/s" % tmp))

    # calculate resolution (now not used - 23/03/2022)
    def calculateResolution(self):
        resolution = 0

        x = float(self.metadata.getMetadataValue(velX))
        y = float(self.metadata.getMetadataValue(velY))
        z = float(self.metadata.getMetadataValue(velZ))

        if self.tmpLevel == "GRD":
            azimuthLookBandwidth = float(self.metadata.getMetadataValue(azimuth_look_bandwidth))
            rangeLookBandwidth = float(self.metadata.getMetadataValue(range_look_bandwidth))
            azimuthLooks = float(self.metadata.getMetadataValue(azimuth_looks))
        elif self.tmpLevel == "SLC":
            azimuthLookBandwidth = float(self.metadata.getMetadataValue(total_processed_bandwidth_azimuth))
            rangeLookBandwidth = 1
            azimuthLooks = 1

        print(("total_processed_bandwidth_azimuth is: %s" % azimuthLookBandwidth))

        # calculate velocity
        velocity = math.sqrt(x ** 2 + y ** 2 + z ** 2)
        print(("velocity is: %s m/s" % velocity))

        # calculate azimuth resolution by dividing velocity by azimuth look bandwidth
        azimuth_resolution = velocity / azimuthLookBandwidth
        print(("azimuth_resolution is: %s" % azimuth_resolution))

        # calculate resolution by multiplying azimuth resolution by azimuth looks
        resolution = azimuth_resolution * azimuthLooks
        resolution = round(resolution, 2)
        print(("resolution is: %s" % resolution))

        print("########################")

        return resolution

    # extract quality
    def extractQuality(self, helper, met):
        pass

    # extract the footprint posList point, ccw, lat lon
    def extractFootprint(self, processInfo):
        new_coords = []
        footprint = []

        first_near = self.metadata.getMetadataValue(coord_first_near)
        first_far = self.metadata.getMetadataValue(coord_first_far)
        last_near = self.metadata.getMetadataValue(coord_last_near)
        last_far = self.metadata.getMetadataValue(coord_last_far)

        orbit_direction = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        look_direction = self.metadata.getMetadataValue(metadata.METADATA_ANTENNA_LOOK_DIRECTION)

        if orbit_direction == "ASCENDING" and look_direction == "RIGHT":
            # footprint = [last_near, last_far, first_far, first_near, last_near]
            footprint = [first_far, first_near, last_near, last_far, first_far]
        elif orbit_direction == "ASCENDING" and look_direction == "LEFT":
            footprint = [first_near, last_near, last_far, first_far, first_near]
        elif orbit_direction == "DESCENDING" and look_direction == "LEFT":  # correct for LEFT LOOK
            footprint = [first_near, first_far, last_far, last_near, first_near]
        elif orbit_direction == "DESCENDING" and look_direction == "RIGHT":  # correct for LEFT LOOK
            footprint = [first_far, last_far, last_near, first_near, first_far]
        else:
            raise Exception("invalid footprint: %s" % footprint)

        # in metadata, coords are shown as: <coord_first_near>1 1 34.82389018847385 -118.02626156859029</coord_first_near>
        # strip first two values below and add the lat and lon to footprint
        for coord in footprint:
            coord = coord.split(' ')
            new_coords.append(coord[2])
            new_coords.append(coord[3])

        footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                    (
                        new_coords[0], new_coords[1],
                        new_coords[2], new_coords[3],
                        new_coords[4], new_coords[5],
                        new_coords[6], new_coords[7],
                        new_coords[8], new_coords[9],
                    )

        print(("footprint: %s" % footprint))

        self.metadata.setMetadataPair("first-footprint", footprint)

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
                print("############### reverse the footprint; before:%s" % (footprint))
            browseIm.reverseFootprint()
            if self.debug != 0:
                print("###############             after;%s" % (browseIm.getFootprint()))
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        flat, flon = browseIm.calculateCenter()
        flat = float(flat)
        flon = float(flon)

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

    def toString(self):
        res = "path:%s" % self.path
        return res

    def dump(self):
        res = "path:%s" % self.path
        print(res)

