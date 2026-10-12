"""This class represents a TerraSAR-X / TanDEM-X Level 1B native product.

A product is one folder named after the product, holding:

- ``<product name>.xml``  main annotation (the entry file of the product)
- ``IMAGEDATA/``          one image file per polarisation layer: COSAR
                          (``.cos``) for SSC products, GeoTIFF otherwise
- ``ANNOTATION/``, ``AUXRASTER/``, ``SUPPORT/``
- ``PREVIEW/``            quicklooks, ``BROWSE.tif`` and ``MAP_PLOT.png``

The DLR DIMS delivery wraps it as
``dims_op_oc_dfd2_<order>/TSX-1.SAR.L1B/<product name>/`` next to a
``readme.html``, an ``iif/`` and a ``tools/`` folder; only the product folder
is the native product.

Where each value is read (main annotation):

- ``generalHeader/mission``: TSX-1 or TDX-1, the platform;
- ``generalHeader/generationTime``: the native processing date;
- ``productInfo/missionInfo``: orbit number and direction;
- ``productInfo/acquisitionInfo``: imaging mode, look direction,
  polarisation mode and layers;
- ``productInfo/productVariantInfo``: SSC / MGD / GEC / EEC, projection;
- ``productInfo/imageDataInfo/imageRaster``: ground range and azimuth
  resolution;
- ``productInfo/sceneInfo``: sensing start / stop, incidence angle at scene
  centre, the four scene corners;
- ``productSpecific/geocodedImageInfo/mapProjection`` (GEC / EEC only): the
  map projection of the geocoded image;
- ``productComponents``: the image data files and the browse image.

The overview PNG is the product browse image (``PREVIEW/BROWSE.tif``, an
8-bit RGB TIFF) re-encoded as PNG, orientation kept as delivered.

Supported product types (EOPF-EOS specialization for TerraSAR-X / TanDEM-X,
Table 2): L1BSL__SLC, L1BSL__MGC, L1BSL__GEC, L1BSL__EEC, L1BSM__SLC,
L1BSM__MGD, L1BSM__GEC, L1BSM__EEC, L1BSC__SLC, L1BSC__MGD, L1BSC__GEC,
L1BSC__EEC, L1BSCW_SLC, L1BSCW_MGD, L1BSCW_GEC, L1BSCW_EEC.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

XML_SUFFIX = ".xml"

# custom metadata keys (mission-local, like RADARSAT-1's)
NATIVE_PRODUCT_VARIANT = 'native_product_variant'
IMAGING_MODE = 'imaging_mode'
PROCESSED_LEVEL_CODE = 'processed_level_code'

# spec Table 16 / ProcessingInformation: every product is level 1B
PROCESSING_LEVEL = "1B"
NATIVE_LEVEL_CODE = "L1B"

# generalHeader mission -> (<MMM> name prefix: 2-digit alias, platform id),
# platformShortName and instrumentShortName (spec Tables 1, 9, 10)
MISSION_MAP = {
    "TSX-1": ("TS", "X", "TerraSAR-X", "TSX-1"),
    "TDX-1": ("TD", "X", "TanDEM-X", "TOR"),
}

# native imaging mode -> operationalMode (spec Table 2): spotlight,
# high resolution spotlight and staring spotlight all map to SL
MODE_MAP = {
    "SL": "SL",
    "HS": "SL",
    "ST": "SL",
    "SM": "SM",
    "SC": "SC",
    "WS": "SCW",
}

# (native product variant, operationalMode) -> product type (spec Table 2).
# The spec names the spotlight MGD product L1BSL__MGC (scope list, Tables 1
# and 2 agree), the other modes ..._MGD.
TYPECODE_MAP = {
    ("SSC", "SL"): "L1BSL__SLC",
    ("MGD", "SL"): "L1BSL__MGC",
    ("GEC", "SL"): "L1BSL__GEC",
    ("EEC", "SL"): "L1BSL__EEC",
    ("SSC", "SM"): "L1BSM__SLC",
    ("MGD", "SM"): "L1BSM__MGD",
    ("GEC", "SM"): "L1BSM__GEC",
    ("EEC", "SM"): "L1BSM__EEC",
    ("SSC", "SC"): "L1BSC__SLC",
    ("MGD", "SC"): "L1BSC__MGD",
    ("GEC", "SC"): "L1BSC__GEC",
    ("EEC", "SC"): "L1BSC__EEC",
    ("SSC", "SCW"): "L1BSCW_SLC",
    ("MGD", "SCW"): "L1BSCW_MGD",
    ("GEC", "SCW"): "L1BSCW_GEC",
    ("EEC", "SCW"): "L1BSCW_EEC",
}

# acquisitionInfo/polarisationMode -> polarisationMode (spec Table 11)
POLARISATION_MODE_MAP = {
    "SINGLE": "S",
    "DUAL": "D",
    "TWIN": "T",
    "QUAD": "Q",
}

POLARISATIONS = ("HH", "HV", "VH", "VV")

# measurements link media type, by image data file extension
MEDIA_TYPES = {
    ".tif": "image/tiff; application=geotiff",
    ".tiff": "image/tiff; application=geotiff",
    # COSAR, the DLR complex SAR binary format: no registered media type
    ".cos": "application/octet-stream",
}

WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"
EPSG_URI = "http://www.opengis.net/def/crs/EPSG/0/%d"


def format_utc(value):
    """datetime -> RFC 3339 with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    return "%s.%03dZ" % (value.strftime("%Y-%m-%dT%H:%M:%S"), value.microsecond // 1000)


def parse_utc(text):
    """'2021-08-02T16:53:58.405374Z' / '2024-03-19T12:31:49.000000' -> datetime
    (the annotation times are UTC; the fraction is cut to microseconds)."""
    match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$", (text or "").strip())
    if not match:
        raise Exception("unexpected TerraSAR-X time format: '%s'" % text)
    value = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
    if match.group(2):
        value = value.replace(microsecond=int((match.group(2) + "000000")[:6]))
    return value


class Product_TerraSARX(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        if not str(self.path).lower().endswith(XML_SUFFIX):
            raise Exception("not a TerraSAR-X main annotation file (.xml): %s" % path)

        self.EO_FOLDER = os.path.dirname(self.path)
        self.productName = os.path.splitext(os.path.basename(self.path))[0]
        self.preview_path = None
        self.tmpSize = 0

        self.root = ET.parse(self.path).getroot()
        if self.root.tag != "level1Product":
            raise Exception("not a TerraSAR-X level 1 product annotation: %s" % path)

        if self.debug != 0:
            print(" init class Product_TerraSARX")

    def text(self, xpath, node=None):
        value = (node if node is not None else self.root).findtext(xpath)
        if value is None or not value.strip():
            raise Exception("missing '%s' in %s" % (xpath, self.path))
        return value.strip()

    def float_value(self, xpath, node=None):
        value = self.text(xpath, node)
        try:
            return float(value)
        except ValueError:
            raise Exception("invalid number in '%s': '%s'" % (xpath, value))

    def component_file(self, component):
        """Path, relative to the product folder, of a productComponents file
        element (e.g. imageData, browseImage)."""
        path = self.text("file/location/path", component)
        name = self.text("file/location/filename", component)
        return name if path == "." else "%s/%s" % (path, name)

    def image_files(self):
        """Image data files relative to the product folder, by layer index."""
        layers = self.root.findall("productComponents/imageData")
        if not layers:
            raise Exception("no imageData in %s" % self.path)
        layers.sort(key=lambda e: int(e.get("layerIndex", "0")))
        return [self.component_file(layer) for layer in layers]

    def browse_file(self):
        browse = self.root.find("productComponents/browseImage")
        if browse is None:
            raise Exception("no browseImage in %s" % self.path)
        path = os.path.join(self.EO_FOLDER, self.component_file(browse))
        if not os.path.isfile(path):
            raise FileNotFoundError("corrupt TerraSAR-X native product (no browse image): %s" % path)
        return path

    # -- product lifecycle ------------------------------------------------

    def afterProductDone(self):
        pass

    def getMetadataInfo(self):
        pass

    # JSON-only mode: the base ingester browse stage is disabled; the preview
    # PNG is written next to the manifest by writeQuicklook().
    def makeBrowses(self, processInfo):
        pass

    def extractToPath(self, folder=None, dont_extract=False):
        """No extraction to disk is needed: the manifest values are read from
        the main annotation in place. Walk the product folder to get the size
        of what lands in measurements/."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)

        self.EXTRACTED_PATH = folder
        self.contentList = []
        self.tmpSize = 0
        for root, dirs, files in os.walk(self.EO_FOLDER):
            for name in files:
                eoFile = os.path.join(root, name)
                self.contentList.append(eoFile)
                self.tmpSize += os.stat(eoFile).st_size
        print((" #### native product: %d file(s), %d bytes"
               % (len(self.contentList), self.tmpSize)))

    def writeQuicklook(self, destPath):
        """Write the overview PNG: the product browse image, re-encoded."""
        from PIL import Image

        source = self.browse_file()
        with Image.open(source) as image:
            if image.mode not in ("L", "RGB", "RGBA"):
                image = image.convert("RGB")
            image.save(destPath, "PNG")
            size = image.size
        self.preview_path = destPath
        print((" #### overview written: %s (%dx%d from %s)"
               % (destPath, size[0], size[1], os.path.basename(source))))
        return destPath

    # -- metadata ---------------------------------------------------------

    def buildTypeCode(self, processInfo):
        variant = self.text("productInfo/productVariantInfo/productVariant")
        imaging_mode = self.text("productInfo/acquisitionInfo/imagingMode")
        mode = MODE_MAP.get(imaging_mode)
        if mode is None:
            raise Exception("unsupported TerraSAR-X imaging mode: '%s'" % imaging_mode)
        typecode = TYPECODE_MAP.get((variant, mode))
        if typecode is None:
            raise Exception("unsupported TerraSAR-X product: %s in imaging mode '%s'"
                            % (variant, imaging_mode))

        self.metadata.setMetadataPair(NATIVE_PRODUCT_VARIANT, variant)
        self.metadata.setMetadataPair(IMAGING_MODE, imaging_mode)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, PROCESSING_LEVEL)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, NATIVE_LEVEL_CODE)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        print(("TYPECODE SET TO: %s (variant %s, imaging mode %s)" % (typecode, variant, imaging_mode)))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met

        # platform: names the package (<MMM> = TSX / TDX) and the manifest
        mission = self.text("generalHeader/mission")
        if mission not in MISSION_MAP:
            raise Exception("unsupported TerraSAR-X mission: '%s'" % mission)
        alias, platform_id, platform, instrument = MISSION_MAP[mission]
        met.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, alias)
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform_id)
        met.setMetadataPair(metadata.METADATA_PLATFORM, platform)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, instrument)

        # sensing times
        start = parse_utc(self.text("productInfo/sceneInfo/start/timeUTC"))
        stop = parse_utc(self.text("productInfo/sceneInfo/stop/timeUTC"))
        start, stop = format_utc(min(start, stop)), format_utc(max(start, stop))
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME,
                            format_utc(parse_utc(self.text("generalHeader/generationTime"))))

        # package creation date (spec Table 7): now, the conversion time
        created = format_utc(datetime.now(timezone.utc))
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # orbit
        orbit = self.text("productInfo/missionInfo/absOrbit")
        if not orbit.isdigit():
            raise Exception("invalid orbit number: '%s'" % orbit)
        met.setMetadataPair(metadata.METADATA_ORBIT, int(orbit))
        orbit_direction = self.text("productInfo/missionInfo/orbitDirection").upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid orbit direction: '%s'" % orbit_direction)
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        # polarisation
        pol_mode = self.text("productInfo/acquisitionInfo/polarisationMode").upper()
        if pol_mode not in POLARISATION_MODE_MAP:
            raise Exception("unsupported polarisation mode: '%s'" % pol_mode)
        channels = [e.text.strip() for e in
                    self.root.findall("productInfo/acquisitionInfo/polarisationList/polLayer")
                    if e.text and e.text.strip()]
        if not channels or any(c not in POLARISATIONS for c in channels):
            raise Exception("invalid polarisation list: %s" % channels)
        met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, POLARISATION_MODE_MAP[pol_mode])
        met.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, ", ".join(channels))

        look = self.text("productInfo/acquisitionInfo/lookDirection").upper()
        if look not in ("RIGHT", "LEFT"):
            raise Exception("invalid look direction: '%s'" % look)
        met.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, look)

        self.buildTypeCode(processInfo)
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the native product size; the base pipeline
        # would fill the eoSIP size here, so mark it as ICEYE does
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        raster = self.root.find("productInfo/imageDataInfo/imageRaster")
        if raster is None:
            raise Exception("no imageDataInfo/imageRaster in %s" % self.path)
        range_resolution = self.float_value("groundRangeResolution", raster)
        azimuth_resolution = self.float_value("azimuthResolution", raster)
        if range_resolution <= 0 or azimuth_resolution <= 0:
            raise Exception("invalid resolution: range=%s azimuth=%s"
                            % (range_resolution, azimuth_resolution))
        resolution = round(max(range_resolution, azimuth_resolution), 3)
        met.addLocalAttribute("rangeResolution", round(range_resolution, 3))
        met.addLocalAttribute("azimuthResolution", round(azimuth_resolution, 3))
        # single figure the spec also asks for: worst of the two directions
        met.addLocalAttribute("resolution", resolution)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)

        incidence = round(self.float_value("productInfo/sceneInfo/sceneCenterCoord/incidenceAngle"), 3)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, incidence)

        met.addLocalAttribute("referenceSystemIdentifier", self.reference_system())

        # the measurements link points at the first image data file, inside
        # the product folder that measurements/ holds
        image = self.image_files()[0]
        extension = os.path.splitext(image)[1].lower()
        if extension not in MEDIA_TYPES:
            raise Exception("unsupported image data file: %s" % image)
        met.addLocalAttribute("nativeDataFile", "%s/%s" % (self.productName, image))
        met.addLocalAttribute("measurementsMediaType", MEDIA_TYPES[extension])

        print(("## resolution range=%s azimuth=%s; incidence=%s"
               % (range_resolution, azimuth_resolution, incidence)))

    def reference_system(self):
        """CRS URI: the map projection of a geocoded (GEC / EEC) product,
        WGS84 geographic for the others (their footprint is geodetic)."""
        projection = self.text("productInfo/productVariantInfo/projection")
        if projection != "MAP":
            return WGS84
        node = self.root.find("productSpecific/geocodedImageInfo/mapProjection")
        if node is None:
            raise Exception("no geocodedImageInfo/mapProjection for the geocoded product %s" % self.path)
        datum = re.sub(r"[\s_-]", "", self.text("geodeticDatumID", node)).upper()
        if datum != "WGS84":
            raise Exception("unsupported geodetic datum '%s' in %s"
                            % (self.text("geodeticDatumID", node), self.path))
        projection_id = self.text("projectionID", node)
        if projection_id == "UTM":
            zone = int(self.text("zoneID", node))
            if not 1 <= zone <= 60:
                raise Exception("invalid UTM zone %d in %s" % (zone, self.path))
            # southern hemisphere zones carry the 10 000 km false northing
            south = self.float_value("mapOrigin/northing", node) > 0
            return EPSG_URI % ((32700 if south else 32600) + zone)
        if projection_id == "UPS":
            north = self.float_value("productInfo/sceneInfo/sceneCenterCoord/lat") > 0
            return EPSG_URI % (32661 if north else 32761)
        raise Exception("unsupported map projection '%s' in %s" % (projection_id, self.path))

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint posList (lat lon pairs, CCW) from the four scene corners,
        ordered around the scene by azimuth time then range time (geocoded
        products give no image row / column for their corners)."""
        corners = []
        for corner in self.root.findall("productInfo/sceneInfo/sceneCornerCoord"):
            corners.append((parse_utc(self.text("azimuthTimeUTC", corner)),
                            self.float_value("rangeTime", corner),
                            self.float_value("lat", corner), self.float_value("lon", corner)))
        if len(corners) != 4:
            raise Exception("expected 4 scene corners in %s, got %d" % (self.path, len(corners)))
        corners.sort()
        (_, _, lat1, lon1), (_, _, lat2, lon2), (_, _, lat3, lon3), (_, _, lat4, lon4) = corners
        # early near / early far / late far / late near
        ring = [(lat1, lon1), (lat2, lon2), (lat4, lon4), (lat3, lon3), (lat1, lon1)]
        footprint = " ".join("%.6f %.6f" % (lat, lon) for lat, lon in ring)
        print(("footprint: %s" % footprint))
        self.metadata.setMetadataPair("first-footprint", footprint)

        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        if not browseIm.getIsCCW():
            browseIm.reverseFootprint()
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())

        flat, flon = browseIm.calculateCenter()
        flat = float(flat)
        flon = float(flon)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))

        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
        if flat < 0:
            flat_token = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat_token = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon_token = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon_token = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat_token)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon_token)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat_token)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon_token)

    def toString(self):
        return "path:%s" % self.path

    def dump(self):
        print(self.toString())
