# -*- coding: cp1252 -*-
#
# this class represent a Pleiades-NEO directory product
import os
import re
import sys
import zipfile

from pathlib import Path

import eoSip_converter.esaProducts.metadata
import eoSip_converter.imageUtil as imageUtil
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.esaProducts import browse_metadata, formatUtils, metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

from xml_nodes import rep_footprint, sipBuilder

__version__ = '1.1.1'
COORD_DECIMAL_PLACES = 6
ANGLE_DECIMAL_PLACES = 2

# for verification
REF_TYPECODE = {
    "NEO_P___1A",
    "NEO_P___2_",
    "NEO_P___3_",
    "NEO_MS__1A",
    "NEO_MS__2_",
    "NEO_MS__3_",
    "NEO_PMS_1A",
    "NEO_PMS_2_",
    "NEO_PMS_3_",
    "NEO_P_S_1A",
    "NEO_P_S_2_",
    "NEO_P_S_3_",
}

def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp

BROWSE_IMAGE_PRIORITY_ORDER = ('_PAN_', '_RGB_')


class Product_Pneo(Product_Directory):
    xmlMapping = {
        metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'Geometric_Data/Use_Area/Located_Geometric_Values/Acquisition_Angles/INCIDENCE_ANGLE',
        metadata.METADATA_RESOLUTION: "Processing_Information/Product_Settings/Sampling_Settings/RESAMPLING_SPACING",
        metadata.METADATA_CLOUD_COVERAGE: "Dataset_Content/CLOUD_COVERAGE",
        metadata.METADATA_START_DATE: "Dataset_Sources/Source_Identification/Strip_Source/IMAGING_DATE",
        metadata.METADATA_START_TIME: "Dataset_Sources/Source_Identification/Strip_Source/IMAGING_TIME",
        metadata.METADATA_PLATFORM_ID: "Dataset_Sources/Source_Identification/Strip_Source/MISSION_INDEX",
        metadata.METADATA_INSTRUMENT_ID: "Dataset_Sources/Source_Identification/Strip_Source/INSTRUMENT_INDEX",
        metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: "Geometric_Data/Use_Area/Located_Geometric_Values/Acquisition_Angles/INCIDENCE_ANGLE_ALONG_TRACK",
        metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: "Geometric_Data/Use_Area/Located_Geometric_Values/Acquisition_Angles/INCIDENCE_ANGLE_ACROSS_TRACK",
        metadata.METADATA_PROCESSING_TIME: "Product_Information/Delivery_Identification/PRODUCTION_DATE",
        "SPECTRAL_PROCESSING": "Processing_Information/Product_Settings/SPECTRAL_PROCESSING",
        "DATASET_TYPE": "Dataset_Identification/DATASET_TYPE",
        metadata.METADATA_NATIVE_PRODUCT_FORMAT: "Raster_Data/Data_Access/DATA_FILE_FORMAT",
        metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: "Coordinate_Reference_System/Projected_CRS/PROJECTED_CRS_CODE"
    }

    # to be removed from xml if value is None
    optionnal_nodes = []

    NO_NUMERIC_VALUE = "-999999"

    # Prefix of the raw data products' metadata files e.g. *.XML
    METADATA_PREFIX = "DIM_PNEO"

    # Prefix of the raw data products' preview images e.g. *.JPG, *.TIF, *.KMZ
    PREVIEW_PREFIX = "PREVIEW_PNEO"
    TIF_SUFFIX = '.TIF'
    JPG2000_SUFFIX = '.JP2'
    IMG_PREFIX = "IMG_PNEO"

    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        # may have several images
        self.metContentName = []
        self.metContent = []
        self.previewContentName = []
        self.previewContent = []
        self.tif_path = []
        self.browseSourceMap = {}
        self.numberOfBrowses = 0
        # preview that are MS (multispectral)
        self.previewIsMs = {}
        if self.debug:
            print(" init class Product_Pneo")

    def getMetadataInfo(self, index=0):
        """Read metadata file"""
        pass

    @property
    def isBundleProduct(self):
        bundle_product_typecodes = (
            "NEO_P_S_1A",
            "NEO_P_S_2_",
            "NEO_P_S_3_",
        )
        if self.metadata.getMetadataValue(metadata.METADATA_TYPECODE) in bundle_product_typecodes:
            return True
        return False

    def makeBrowsesFromTifs(self, processInfo):
        import PIL

        if self.debug != 0:
            print(" makeBrowsesFromTifs: number of browses: %s" % self.numberOfBrowses)
        processInfo.addLog(" makeBrowsesFromTifs: number of browses: %s" % self.numberOfBrowses)

        anEosip = processInfo.destProduct
        self.browseRelPath = os.path.dirname(processInfo.destProduct.folder)

        # for every browse, # browse where extracted during extractToPath
        allBrowseMade = []

        regex_expr = r'(^.*?\/?(IMG_PNEO[0-9](?:_[A-Z]*)?_[0-9]*_(\S*?)_(\S*?)_\S*?_([A-Z0-9]*)_([A-Z0-9]*)\.(TIF|JP2))$)'
        regex_group_keys = ('fullPath', 'filename', 'band', 'processLevel', 'colors', 'mosaicTile', 'fileType')
        raw_images = []
        for browseSrcPath in self.tif_path:
            match = re.search(regex_expr, browseSrcPath)

            # If match is found, create dictionary
            if match:
                result_dict = {key: match.group(i + 1) for i, key in enumerate(regex_group_keys)}
                raw_images.append(result_dict)

        if len(raw_images) == 0:
            raise RuntimeError(f"No native images found matching regex '{regex_expr}'")

        possible_bands = ('PAN', 'PMS-FS', 'MS-FS', 'PMS', 'MS', 'PMS-N', 'PMS-X')
        possible_colors = ('P', 'RGB', 'RGBN', 'NED', 'RGB', 'NRG')

        # Just keep highest-priority image type(s)
        row_images_colors = set([img['colors'] for img in raw_images])
        row_images_colors_to_keep = sorted(row_images_colors, key=lambda x: possible_colors.index(x))[:2 if self.isBundleProduct else 1]
        raw_images = list(filter(lambda x: x['colors'] in row_images_colors_to_keep, raw_images))
        raw_images = sorted(raw_images, key=lambda x: possible_colors.index(x['colors']))
        raw_images = sorted(raw_images, key=lambda x: possible_bands.index(x['band']))
        raw_images = sorted(raw_images, key=lambda x: x['mosaicTile'])  # R1C1 (top-left tile first)

        tile_names = sorted(list(set([im['mosaicTile'] for im in raw_images])))
        raw_images_by_color = {
            col: list(filter(lambda x: x['colors'] == col, raw_images))
            for col in row_images_colors_to_keep
        }

        # Deal with mosaiced images
        if len(tile_names) > 1:
            tmp_dir = Path(raw_images[0]['fullPath']).parent
            image_file_type = Path(raw_images[0]['fullPath']).suffix.lstrip('.')
            ncols = max([int(tile_name[3]) for tile_name in tile_names])
            raw_images = []
            for color in row_images_colors_to_keep:
                tiles_for_color = raw_images_by_color[color]
                row = []
                image_arr = []
                for tile in tiles_for_color:
                    row.append(tile)
                    if len(row) >= ncols:
                        image_arr.append(row)
                        row = []

                tmp_mosaic_image = tmp_dir / f"{Path(tile['filename']).stem[:-4]}MOSAIC.{image_file_type}"
                imageUtil.create_mosaic_pyvips(
                    [[im['fullPath'] for im in row] for row in image_arr],
                    tmp_mosaic_image
                )
                raw_images.append(
                    {
                        'fullPath': str(tmp_mosaic_image),
                        'filename': tmp_mosaic_image.name,
                        'band': tile['band'],
                        'processLevel': tile['processLevel'],
                        'colors': tile['colors'],
                        'mosaicTile': '*',
                        'fileType': tmp_mosaic_image.suffix.lstrip('.')
                    }
                )

        # Remove any raw images of which there are more than 1 of in that band
        tmp = []
        for raw_image in raw_images:
            if raw_image['band'] not in [ri['band'] for ri in tmp]:
                tmp.append(raw_image)
        raw_images = tmp[:2 if self.isBundleProduct else 1]

        # for browseSrcPath in self.tif_path:
        for n, raw_image in enumerate(raw_images):
            # Two browse images maximum
            if n > 1 or (n == 1 and not self.isBundleProduct):
                break

            browseSrcPath = raw_image['fullPath']
            bName = raw_image['filename']

            print("\n makeBrowsesFromTifs: doings n=%s: %s" % (n, browseSrcPath))
            processInfo.addLog(" makeBrowsesFromTifs: doings n=%s: %s" % (n, browseSrcPath))

            # Assign default BI, but also ensure only one browse image (and correct naming) if bundle product
            biX = 'BI'
            if len(raw_images) > 1 and self.isBundleProduct:
                # If is the default browse image, make it 'BID', not 'BI' (secondary browse image only)
                if n == 0:
                    biX += 'D'

            browseName = processInfo.destProduct.eoProductName
            browseDestPath = "%s/%s.%s.PNG" % (self.browseRelPath, browseName, biX)
            print(("##  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath)))
            processInfo.addLog("##  browse image[%s] name done:  name=%s; path=%s" % (n, bName, browseDestPath))

            if self.debug != 0:
                print(" makeBrowsesFromTifs: tif has NO preview")
            processInfo.addLog(" makeBrowsesFromTifs: tif has NO preview")

            # set map browse-created -> browse source
            self.browseSourceMap[os.path.basename(browseDestPath)] = os.path.basename(browseSrcPath)

            allBrowseMade.append(browseDestPath)
            imageUtil.makeBrowse_v2(
                type="PNG", src=browseSrcPath, dest=browseDestPath, showTraceback=True
            )

            image_mean_brightness, image_std = imageUtil.image_mean_and_std(browseDestPath)
            img = PIL.Image.open(browseDestPath)
            img = PIL.ImageEnhance.Brightness(img)
            img = img.enhance(90. / image_mean_brightness)
            img.save(browseDestPath)

        for browseDestPath in allBrowseMade:
            bName = os.path.basename(browseDestPath)
            anEosip.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  browse image[%s] added: name=%s; path=%s" % (n, bName, browseDestPath))
            # set AM timne if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[browseDestPath]
            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()

            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != 0:
                print("browseChoiceBlock:%s" % (browseChoiceBlock))
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

            processInfo.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))


    def makeBrowses(self, processInfo):
        if self.debug:
            print(" makeBrowses: number of browses:%s" % len(self.previewContentName))
        processInfo.addLog(
            " makeBrowses: number of browses:%s" % len(self.previewContentName)
        )
        n = 0
        anEosip = processInfo.destProduct
        self.makeBrowsesFromTifs(processInfo)

    def extractToPath(self, folder=None, dont_extract=False):
        """
        Extract the relevant Pleiades-NEO files in to the working folder. This
        includes metadata xml files, and preview images
        """
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)

        if self.debug:
            print(
                " will extract directory product '%s' to path: %s" % (self.path, folder)
            )

        self.contentList = []
        self.EXTRACTED_PATH = folder
        with open(self.path, "rb") as fh:
            with zipfile.ZipFile(fh) as z:
                self.contentList = []

                n = 0
                self.isPneo = False
                for name in z.namelist():
                    n = n + 1
                    print("  extract[%d]:%s" % (n, name))

                    # keep metadata and preview data
                    if name.find(self.METADATA_PREFIX) >= 0:  # metadata
                        self.metContentName.append(name)
                        if self.debug:
                            print("   metContentName:%s" % name)
                        data = z.read(name)

                        if not dont_extract:
                            parent = os.path.dirname(folder + os.sep + name)

                            if not os.path.exists(parent):
                                os.makedirs(parent)

                            with open(folder + "/" + name, "wb") as outfile:
                                outfile.write(data)

                        self.metContent.append(data)
                    elif name.find(self.PREVIEW_PREFIX) >= 0 and name.upper().endswith(
                        ".JPG"
                    ):  # preview
                        self.previewContentName.append(name)
                        if self.debug:
                            print("   previewContentName:%s" % name)
                        data = z.read(name)
                        if dont_extract != True:
                            parent = os.path.dirname(folder + "/" + name)

                            if not os.path.exists(parent):
                                os.makedirs(parent)

                            with open(folder + os.sep + name, "wb") as outfile:
                                outfile.write(data)

                        self.previewContent.append(data)
                    elif any(name.lower().endswith(sfx) for sfx in ('.tif', '.jp2')) :
                        if dont_extract is False:
                            parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                            if not os.path.exists(parent):
                                os.makedirs(parent)
                            aTifPath = self.EXTRACTED_PATH + '/' + name

                            with open(aTifPath, 'wb') as outfile:
                                outfile.write(z.read(name))

                            self.tif_path.append(aTifPath)

                    self.contentList.append(name)

                    # P-NEO test
                    if name.find(self.IMG_PREFIX) > 0:
                        self.isPneo = True

                self.numberOfBrowses = len(self.tif_path)

        if not self.isPneo:
            raise Exception("is not a Pleiades-NEO product")

    def extractMetadata(self, met=None):
        if met is None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")

        # they may be several DIMAP files, two in bundle.
        # metadata for US may differ in SPECTRAL_PROCESSING and DATASET_TYPE
        metNum = 0
        self.SPECTRAL_PROCESSING = {}
        self.DATASET_TYPE = {}
        self.nbands = 0
        self.spectral_processing = []
        for metContent in self.metContent:
            # metContent=self.metContent[0]

            # extact metadata
            helper = xmlHelper.XmlHelper()
            # helper.setDebug(1)
            helper.setData(metContent)
            helper.parseData()

            # get fields
            resultList = []
            op_element = helper.getRootNode()
            num_added = 0

            # Get number of bands
            nbands = helper.getNodeText(
                helper.getFirstNodeByPath(
                    path='Raster_Data/Raster_Dimensions/NBANDS'
                )
            )
            if nbands is not None and int(nbands) > self.nbands:
                self.nbands = int(nbands)

            self.spectral_processing.append(
                helper.getNodeText(
                    helper.getFirstNodeByPath(
                        path='Processing_Information/Product_Settings/SPECTRAL_PROCESSING'
                    )
                )
            )

            for field in self.xmlMapping:
                if self.xmlMapping[field].find("@") >= 0:
                    attr = self.xmlMapping[field].split("@")[1]
                    path = self.xmlMapping[field].split("@")[0]
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

                        # if self.DEBUG!=0:
                print("  metnum[%s] -->%s=%s" % (metNum, field, aValue))

                if field == "SPECTRAL_PROCESSING":
                    self.SPECTRAL_PROCESSING[aValue] = aValue
                elif field == "DATASET_TYPE":
                    self.DATASET_TYPE[aValue] = aValue

                met: eoSip_converter.esaProducts.metadata.Metadata
                met.setMetadataPair(field, aValue)
                num_added = num_added + 1

            metNum += 1

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        met.addLocalAttribute("originalName", self.origName)

        self.metadata = met

        # refine
        self.refineMetadata(helper)

    def refineMetadata(self, xmlHelper_: xmlHelper.XmlHelper):
        """Refine the metadata"""
        self.metadata.setMetadataPair(
            metadata.METADATA_STOP_DATE,
            self.metadata.getMetadataValue(metadata.METADATA_START_DATE),
        )
        self.metadata.setMetadataPair(
            metadata.METADATA_RESOLUTION_UNIT, 'm'
        )
        # time in product has already the final Z, remove it
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        if tmp.endswith("Z"):
            tmp = tmp[0:-1]
        tmp = formatUtils.removeMsecFromTimeString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(
            metadata.METADATA_TIME_POSITION,
            "%sT%sZ"
            % (
                self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
                self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME),
            ),
        )

        current_frame = self.metadata.getMetadataValue(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER)
        if not current_frame:
            alt_native_crs_node_path = "Coordinate_Reference_System/Geodetic_CRS/GEODETIC_CRS_CODE"
            resultList = []
            xmlHelper_.getNodeByPath(None, alt_native_crs_node_path, None, resultList)
            current_frame = xmlHelper_.getNodeText(resultList[0])

        self.metadata.setMetadataPair(
            metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER,
            ':'.join([_ for _ in current_frame.split(':') if _][-2:])
        )
        # processing date
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        tmp1 = formatUtils.removeMsecFromDateTimeString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp1)

        # find strip id like: <COMPONENT_PATH href="LINEAGE/STRIP_DS_PHR1A_201308191759419_FR1_PX_W105N39_0224_08756_DIM.XML"/>
        path = "Dataset_Content/Dataset_Components/Component/COMPONENT_PATH"
        resultList = []
        xmlHelper_.getNodeByPath(None, path, None, resultList)

        if self.debug:
            print("component paths; len=%s" % len(resultList))

        lineage = None
        for item in resultList:
            for attr in list(item.attributes.items()):  # tuples
                for n in range(len(attr) // 2):
                    key = attr[n]
                    value = attr[n + 1]
                    if key == "href":
                        if value.startswith("LINEAGE/PROCESSING_PNEO"):
                            lineage = value
                            if self.debug:
                                print(" found the LINEAGE/PROCESSING_PNEO:%s" % lineage)
                            break
        if lineage is None:
            raise Exception("can not find Pleiades-NEO LINEAGE")

        path = "Dataset_Content/Dataset_Extent/Vertex/LON"
        xml_lon_elements = []
        xmlHelper_.getNodeByPath(None, path, None, xml_lon_elements)
        mean_lon = sum(
            map(
                lambda lon_element: float(xmlHelper_.getNodeText(lon_element)),
                xml_lon_elements,
            )
        ) / len(xml_lon_elements)

        path = "Dataset_Content/Dataset_Extent/Vertex/LAT"
        xml_lat_elements = []
        xmlHelper_.getNodeByPath(None, path, None, xml_lat_elements)
        mean_lat = sum(
            map(
                lambda lat_element: float(xmlHelper_.getNodeText(lat_element)),
                xml_lat_elements,
            )
        ) / len(xml_lat_elements)

        lonLat = "{}{:03.0f}{}{:02.0f}".format(
            "W" if mean_lon < 0 else "E", abs(mean_lon),
            "N" if mean_lat > 0 else "S", abs(mean_lat),
        )

        if self.debug:
            print(" LINEAGE lonLat:%s" % lonLat)

        # NEW: get it from scene center bellow in extract footprint
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, lonLat[4:])
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, lonLat[0:4])
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, '000')
        # self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, '000')
        self.metadata.setMetadataPair(
            metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, lonLat[4:]
        )
        self.metadata.setMetadataPair(
            metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, lonLat[0:4]
        )

        # Get processing software version
        node = xmlHelper_.getFirstNodeByPath(None, "Processing_Information/Production_Facility/SOFTWARE")
        software_version = xmlHelper_.getNodeAttributeText(node, "version")
        if ';' in software_version:
            software_version = software_version.split(';')[0]
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, software_version)

        # get version from: <DATASET_NAME version="1.0">ORT_SPOT7_20140917_102524900_000</DATASET_NAME> line 12
        path = 'Dataset_Identification/DATASET_NAME'
        resultList = []
        xmlHelper_.getNodeByPath(None, path, None, resultList)
        if len(resultList) == 1:
            # version is like: V_03_09
            # 2019-07-26: OR V2.6
            version = xmlHelper_.getNodeAttributeText(resultList[0], "version")
            print(
                "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ print SOFTWARE VERSION:%s" % version
            )
            # fileVersion = version.replace('.','')
            if version.startswith("V_"):
                fileVersion = version.replace("V_", "")
            elif version.startswith("0"):
                fileVersion = version[1:]
            elif version.startswith("V"):
                fileVersion = version[1:]
            else:
                fileVersion = version

            # DELETE ME IF NOT NEEDED
            fileVersion = fileVersion.replace("_", "").replace(".", "")
            # DELETE ABOVE F NOT NEEDED AND UNCOMMENT BELOW LINE
            # fileVersion = fileVersion.replace("_", "").replace(".", "0")

            if len(fileVersion) > 3:
                fileVersion = fileVersion[0:3]
            elif len(fileVersion) < 3:
                fileVersion = formatUtils.leftPadString(fileVersion, 3, "0")

            counter = self.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
            if counter == sipBuilder.VALUE_NONE:
                counter = "1"
            # self.metadata.setMetadataPair(
            #     metadata.METADATA_SIP_VERSION, fileVersion
            # )
            # self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)  # in the MD
            self.metadata.setMetadataPair(
                metadata.METADATA_PRODUCT_VERSION, fileVersion
            )  # in the MD
            # if self.DEBUG!=0:
            print(" version:%s; fileVersion:%s" % (version, fileVersion))
            print(
                "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ print SOFTWARE VERSION final:%s"
                % self.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
            )
            # sys.exit(0)
        else:
            raise Exception("can not retrieve dataset version")

        # set second to 00
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        toks = tmp.split(":")
        self.metadata.setMetadataPair(
            metadata.METADATA_START_TIME, "%s:%s:00" % (toks[0], toks[1])
        )

        # remove optionnal nodes
        for item in self.optionnal_nodes:
            tmp = self.metadata.getMetadataValue(item)
            # print "test for optional node:%s=%s; type:%s" % (item, tmp, type(tmp))
            if tmp is None:  # or tmp == sipBuilder.VALUE_NOT_PRESENT:
                # self.metadata.deleteMetadata(item)
                # print " removed optional node:%s=%s; type:%s" % (item, tmp, type(item))
                self.metadata.setMetadataPair(item, self.NO_NUMERIC_VALUE)
                print(
                    " set optional node:%s=%s; type:%s to NO_NUMERIC_VALUE:%s"
                    % (item, tmp, type(item), self.NO_NUMERIC_VALUE)
                )

        self.buildTypeCode()
        self.extractFootprint(xmlHelper_)

        # Refine accuracy of footprint coordinates to 6 decimal places (0.1m accuracy at the equator)
        footprint_str = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        footprint_cw_str = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT_CW)
        scene_centre_str = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)

        self.metadata.setMetadataPair(
            metadata.METADATA_FOOTPRINT,
            ' '.join([format(float(_), f'.{COORD_DECIMAL_PLACES}f') for _ in footprint_str.split()])
        )
        self.metadata.setMetadataPair(
            metadata.METADATA_FOOTPRINT_CW,
            ' '.join([format(float(_), f'.{COORD_DECIMAL_PLACES}f') for _ in footprint_cw_str.split()])
        )
        self.metadata.setMetadataPair(
            metadata.METADATA_SCENE_CENTER,
            ' '.join([format(float(_), f'.{COORD_DECIMAL_PLACES}f') for _ in scene_centre_str.split()])
        )

        if self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL) == '3':
            bbox_str = self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)
            bbox_cw_str = self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX_CW_CLOSED)
            self.metadata.setMetadataPair(
                metadata.METADATA_BOUNDING_BOX,
                ' '.join([format(float(_), f'.{COORD_DECIMAL_PLACES}f') for _ in bbox_str.split()])
            )
            self.metadata.setMetadataPair(
                metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                ' '.join([format(float(_), f'.{COORD_DECIMAL_PLACES}f') for _ in bbox_cw_str.split()])
            )

            if self.metadata.localAttributeExists("boundingBox"):
                self.metadata.removeLocalAttribute("boundingBox")

            self.metadata.addLocalAttribute(
                "boundingBox",
                self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX),
            )

        product_typecode = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        # For panchromatic products
        if product_typecode[4:7] == 'P__':
            band_combination = 'PAN'
        # For multispectral products
        elif product_typecode[4:7] == 'MS_':
            if self.nbands == 4:
                band_combination = 'MS 4-bands'
            elif self.nbands == 6:
                band_combination = 'MS 6-bands'
            else:
                raise Exception("unexpected number of bands for MS product: %s" % self.nbands)
        # For bundle products
        elif product_typecode[4:7] == 'P_S':
            if self.nbands == 4:
                band_combination = 'P_S 4-bands'
            elif self.nbands == 6:
                band_combination = 'P_S 6-bands'
            else:
                raise Exception("unexpected number of bands for P_S product: %s" % self.nbands)
        # For pansharpened products
        elif product_typecode[4:7] == 'PMS':
            if self.nbands == 4:
                band_combination = 'PMS 4-bands'
            elif self.nbands == 6:
                band_combination = 'PMS 6-bands'
            elif self.nbands == 3:
                if 'PMS-X' in self.spectral_processing:
                    band_combination = 'PMS 3-bands (NIRRG)'
                elif 'PMS-N' in self.spectral_processing:
                    band_combination = 'PMS 3-bands (RGB)'
                else:
                    raise Exception(
                        "unexpected spectral processing value(s) for 3-bands: %s" % ', '.join(self.spectral_processing)
                    )
            else:
                raise Exception("unexpected number of bands for PMS product: %s" % self.nbands)
        else:
            raise Exception("unexpected product typecode: %s" % product_typecode)

        self.metadata.addLocalAttribute("bandCombination", band_combination)
        angle_metadata = (
            metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE,
            metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE,
            metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE,
        )
        for angle_datum in angle_metadata:
            value = self.metadata.getMetadataValue(angle_datum)
            self.metadata.setMetadataPair(angle_datum, format(float(value), f'.{ANGLE_DECIMAL_PLACES}f'))

    # NEO_P___1A (SPOT 6-7 Panchromatic primary)  ==> only spectral processing 'P'
    # NEO_P___3_ (SPOT 6-7 Panchromatic ortho)    ==> only spectral processing 'P'
    # NEO_MS__1A (SPOT 6-7 Multispectral primary) ==> only spectral processing 'MS'
    # NEO_MS__3_ (SPOT 6-7 Multispectral ortho)   ==> only spectral processing 'MS'
    # NEO_PMS_1A (SPOT 6-7 PanSharpened primary)  ==> only spectral processing 'PMS'
    # NEO_PMS_3_ (SPOT 6-7 PanSharpened ortho)    ==> only spectral processing 'PMS'
    # NEO_P_S_1A (SPOT 6-7 Bundle primary)        ==> spectral processing 'P' + 'MS'
    def buildTypeCode(self):
        sensor = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_NAME)
        if sensor is None:
            raise Exception("can not construct typecode: sensor is None")

        for key in list(self.SPECTRAL_PROCESSING.keys()):
            print(
                "%s TODO SPECTRAL_PROCESSING:%s"
                % (self.origName, self.SPECTRAL_PROCESSING[key])
            )
        for key in list(self.DATASET_TYPE.keys()):
            print("%s TODO DATASET_TYPE:%s" % (self.origName, self.DATASET_TYPE[key]))

        n = 0
        mode = "##"
        for key in list(self.SPECTRAL_PROCESSING.keys()):
            value = self.SPECTRAL_PROCESSING[key]
            print(
                "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ self.SPECTRAL_PROCESSING key[%s]:%s; value:%s"
                % (n, key, value)
            )
            print(
                "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ self.SPECTRAL_PROCESSING key:%s; value:%s"
                % (key, value)
            )
            self.processInfo.infoKeeper.addInfo(
                "%s_SPECTRAL_PROCESSING" % self.origName, value
            )
            n += 1

        # From P-NEO user guide, the spectral processing can be:
        # - MS: Multispectral
        # - PAN: Panchromatic
        # - MS-FS: Multispectral Full Scene
        # - PMS: PanSharpened
        # - PMS-FS: PanSharpened Full Scene
        # - PMS-X: PanSharpened with X band
        # - PMS-N: PanSharpened with NIR band
        if len(list(self.SPECTRAL_PROCESSING.keys())) == 2:  # should be p + MS
            if any([sp in self.SPECTRAL_PROCESSING for sp in ("MS-FS", "MS", "PMS-FS")]) and "PAN" in self.SPECTRAL_PROCESSING:
                mode = "P_S"
            else:
                raise Exception(
                    "strange spectral_mode pair: %s %s"
                    % (
                        list(self.SPECTRAL_PROCESSING.keys())[0],
                        list(self.SPECTRAL_PROCESSING.keys())[1],
                    )
                )
        else:
            mode = list(self.SPECTRAL_PROCESSING.keys())[0]

        if mode == 'MS-FS':
            mode = 'MS_'

        if len(mode) < 3:
            mode = formatUtils.rightPadString(mode, 3, "_")

        if mode in ('PMS-FS', 'PMS-N', 'PMS-X'):
            mode = 'PMS'

        tmp = self.metadata.getMetadataValue("DATASET_TYPE")
        plevel = "##"
        if tmp == "RASTER_ORTHO":
            plevel = "3_"
        elif tmp == "RASTER_SENSOR":
            plevel = "1A"
        elif tmp == "RASTER_PROJECTED":
            plevel = "2_"

        typecode = "%s_%s_%s" % (sensor, mode, plevel)
        if not typecode in REF_TYPECODE:
            raise Exception(
                "buildTypeCode; unknown typecode:%s; level:%s" % (typecode, tmp)
            )

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

        if plevel == "3_":
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, "3")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, plevel)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)

        if self.isBundleProduct:
            self.metadata.deleteMetadata(metadata.METADATA_RESOLUTION)
            self.metadata.deleteMetadata(metadata.METADATA_RESOLUTION_UNIT)

    def extractQuality(self, helper, met):
        """Extract quality"""
        pass

    def extractFootprint(self, helper):
        """Extract the footprint posList point, ccw, lat lon"""
        n = 0
        for browsePath in self.previewContentName:
            if self.debug:
                print(" extractFootprint, use preview[%s]:%s" % (n, browsePath))
            # get preview resolution
            try:
                imw, imh = imageUtil.get_image_size(
                    "%s/%s" % (self.processInfo.workFolder, browsePath)
                )
                if self.debug:
                    print(
                        "  extractFootprint preview image size: w=%s; h=%s" % (imw, imh)
                    )
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(
                    " ERROR getting preview image size:%s %s\n%s"
                    % (exc_type, exc_obj, exc_tb)
                )
                raise Exception("ERROR getting preview image size")

            # get product image resolution
            tmpNodes = []
            helper.getNodeByPath(None, "Raster_Data/Raster_Dimensions", None, tmpNodes)
            if len(tmpNodes) == 1:
                ncols = helper.getNodeText(
                    helper.getFirstNodeByPath(tmpNodes[0], "NCOLS", None)
                )
                nrows = helper.getNodeText(
                    helper.getFirstNodeByPath(tmpNodes[0], "NROWS", None)
                )
                if self.debug:
                    print(
                        "  extractFootprint product image size: w=%s; h=%s"
                        % (ncols, nrows)
                    )
            else:
                raise Exception("ERROR getting Raster_Dimensions")

            rcol = int(ncols) / imw
            rrow = int(nrows) / imh
            # print "  ############# ratio product/preview: rcol=%s; rrow=%s" % (rcol, rrow)

            footprint = ""
            rowCol = ""
            nodes = []
            # helper.setDebug(1)
            helper.getNodeByPath(None, "Dataset_Content/Dataset_Extent", None, nodes)
            k = 0
            if len(nodes) == 1:
                # get vertex
                vertexList = helper.getNodeChildrenByName(nodes[0], "Vertex")
                if len(vertexList) == 0:
                    raise Exception("can not find footprint vertex")

                closePoint = ""
                closeRowCol = ""
                for node in vertexList:  # CW first top left
                    lon = helper.getNodeText(
                        helper.getFirstNodeByPath(node, "LON", None)
                    )
                    lat = helper.getNodeText(
                        helper.getFirstNodeByPath(node, "LAT", None)
                    )
                    row = helper.getNodeText(
                        helper.getFirstNodeByPath(node, "ROW", None)
                    )
                    col = helper.getNodeText(
                        helper.getFirstNodeByPath(node, "COL", None)
                    )
                    if self.debug:
                        print(
                            "  ############# vertex %d: lon:%s  lat:%s  row:%s  col:%s"
                            % (k, lon, lat, row, col)
                        )
                    if len(footprint) > 0:
                        footprint = "%s " % footprint
                    if len(rowCol) > 0:
                        rowCol = "%s " % rowCol
                    footprint = "%s%s %s" % (
                        footprint,
                        formatUtils.EEEtoNumber(lat),
                        formatUtils.EEEtoNumber(lon),
                    )
                    okRow = int(row) / rcol
                    okCol = int(col) / rrow
                    if row == "1":
                        okRow = 1
                    if col == "1":
                        okCol = 1
                    rowCol = "%s%s %s" % (rowCol, okRow, okCol)

                    if k == 0:
                        closePoint = "%s %s" % (
                            formatUtils.EEEtoNumber(lat),
                            formatUtils.EEEtoNumber(lon),
                        )
                        closeRowCol = "%s %s" % (okRow, okCol)
                    k += 1

            else:
                raise Exception("ERROR getting Dataset_Extent")

            footprint = "%s %s" % (footprint, closePoint)
            rowCol = "%s %s" % (rowCol, closeRowCol)
            if self.debug:
                print("  ############# footprint=%s; rowCol=%s" % (footprint, rowCol))

            # number of nodes in footprint
            self.metadata.setMetadataPair(
                browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "%s" % (k + 1)
            )

            # get center
            tmpNodes = []
            helper.getNodeByPath(
                None, "Dataset_Content/Dataset_Extent/Center", None, tmpNodes
            )
            if len(tmpNodes) == 1:
                clon = helper.getNodeText(
                    helper.getFirstNodeByPath(tmpNodes[0], "LON", None)
                )
                clat = helper.getNodeText(
                    helper.getFirstNodeByPath(tmpNodes[0], "LAT", None)
                )
                self.metadata.setMetadataPair(
                    metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat
                )
                self.metadata.setMetadataPair(
                    metadata.METADATA_SCENE_CENTER_LON, "%s" % clon
                )
                self.metadata.setMetadataPair(
                    metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon)
                )
            else:
                raise Exception("ERROR getting Dataset_Extent/Center")

            flat = float(clat)
            flon = float(clon)
            mseclon = abs(int((flon - int(flon)) * 1000))
            mseclat = abs(int((flat - int(flat)) * 1000))
            if flat < 0:
                flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, "0")
            else:
                flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, "0")
            if flon < 0:
                flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, "0")
            else:
                flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, "0")
            self.metadata.setMetadataPair(
                metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat
            )
            self.metadata.setMetadataPair(
                metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon
            )
            self.metadata.setMetadataPair(
                metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                formatUtils.leftPadString("%s" % int(mseclat), 3, "0"),
            )
            self.metadata.setMetadataPair(
                metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                formatUtils.leftPadString("%s" % int(mseclon), 3, "0"),
            )

            # make sure the footprint is CCW
            # also prepare CW for EoliSa index and shopcart
            browseIm = BrowseImage()
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
            browseIm.setColRowList(rowCol)
            if self.debug:
                print("browseIm:%s" % browseIm.info())
            if not browseIm.getIsCCW():
                # keep for eolisa
                self.metadata.setMetadataPair(
                    metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint()
                )

                # and reverse
                if self.debug:
                    print(
                        "############### reverse the footprint; before:%s; colRowList:%s"
                        % (footprint, rowCol)
                    )
                browseIm.reverseFootprint()
                if self.debug:
                    print(
                        "###############             after;%s; colRowList:%s"
                        % (browseIm.getFootprint(), browseIm.getColRowList())
                    )
                self.metadata.setMetadataPair(
                    metadata.METADATA_FOOTPRINT, browseIm.getFootprint()
                )
                self.metadata.setMetadataPair(
                    metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, browseIm.getColRowList()
                )
            else:
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                self.metadata.setMetadataPair(
                    metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, rowCol
                )

                # reverse for eolisa
                self.metadata.setMetadataPair(
                    metadata.METADATA_FOOTPRINT_CW,
                    browseIm.reverseSomeFootprint(footprint),
                )

            # boundingBox is needed in the localAttributes ONLY for level 3_
            level = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            # raise Exception("processing level:'%s'" % level)
            if level == "3":
                self.metadata.setMetadataPair(
                    metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox
                )
                closedBoundingBox = "%s %s %s" % (
                    browseIm.boondingBox,
                    browseIm.boondingBox.split(" ")[0],
                    browseIm.boondingBox.split(" ")[1],
                )
                self.metadata.setMetadataPair(
                    metadata.METADATA_BOUNDING_BOX_CW_CLOSED,
                    browseIm.reverseSomeFootprint(closedBoundingBox),
                )

                if not self.metadata.localAttributeExists("boundingBox"):
                    self.metadata.addLocalAttribute(
                        "boundingBox",
                        self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX),
                    )

            n += 1

        return footprint, rowCol

    def toString(self) -> str:
        res = "path:%s" % self.path
        return res

    def dump(self):
        res = "path:%s" % self.path
        print(res)
