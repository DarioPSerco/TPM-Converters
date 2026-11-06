"""This class represents a RADARSAT-2 native product.

A product is one folder, named by MDA
``RS2_OK<order>_PK<product>_DK<delivery>_<beam>_<date>_<time>_<pols>_<type>``,
holding:

- ``product.xml``         the product annotation (the entry file)
- ``imagery_<pol>.tif``   one image file per polarisation (GeoTIFF; NITF
                          ``.ntf`` when ordered so)
- ``BrowseImage.tif``     the product browse image
- ``lutBeta.xml`` / ``lutSigma.xml`` / ``lutGamma.xml``, ``product.kml``,
  ``productPreview.html``, ``schemas/``

Every product has the same entry file name, so the native product name -
the lineage citation, which run_mission.py and the packager use to find the
product back - is the product folder name.

Where each value is read (``product.xml``, default namespace stripped):

- ``sourceAttributes/beamModeMnemonic``: the beam mode -> operationalMode;
- ``sourceAttributes/radarParameters``: polarisations, antenna pointing;
- ``sourceAttributes/orbitAndAttitude/orbitInformation``: pass direction,
  orbit data file (``<orbit>_<kind>.ORB``: the orbit number), state vectors;
- ``imageGenerationParameters/generalProcessingInformation``: product type
  (SLC / SGF / SGX / SSG / SPG / SCN / SCW / SCF / SCS), processing time;
- ``imageGenerationParameters/sarProcessingInformation``: zero Doppler
  first / last line times, near / far range incidence angles, range and
  azimuth look bandwidths, satellite height;
- ``imageAttributes``: image files, geolocation grid (footprint) and, for a
  map image (SSG / SPG), its map projection.

The orbit number is not in ``product.xml`` itself: it is the leading number
of the orbit data file name, else the ``Orbit Number`` line of a
``*.prodReport`` file in the folder, else the cfg ``METADATA_ORBIT`` with a
warning.

Supported product types (EOPF-EOS specialization for RADARSAT-2, Table 2):
the 41 codes of ``TYPECODE_MAP``.
"""
import math
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

ENTRY_NAME = "product.xml"
BROWSE_NAME = "BrowseImage.tif"
PROD_REPORT_SUFFIX = ".prodReport"

# custom metadata keys (mission-local, like RADARSAT-1's)
NATIVE_PRODUCT_TYPE = 'native_product_type'
BEAM_MODE = 'beam_mode'
PROCESSED_LEVEL_CODE = 'processed_level_code'

# beam mode mnemonic -> operationalMode (spec Table 2). RADARSAT-2 beam
# modes are folded on the specialization's RADARSAT-1 style modes:
# single beam (BS), finer resolution (BSF), wider swath (BSW), wider swath
# and finer resolution (BSWF), multi-look (ML / MLW), spotlight, ScanSAR.
# First match wins: the wide variants are listed before their base mode.
MODE_RULES = (
    (r"SLA\d+", "SL"),
    (r"SCN[AB]?", "SCN"),
    (r"SCW[AB]?", "SCW"),
    (r"MF\d+[NF]?W", "MLW"),           # Wide Multi-Look Fine
    (r"MF\d+[NF]?", "ML"),             # Multi-Look Fine
    (r"U\d+W\d", "BSWF"),              # Wide Ultra-Fine
    (r"U\d+", "BSF"),                  # Ultra-Fine
    (r"XF0[WS]\d", "BSWF"),            # Extra-Fine (wide swath, 5 m)
    (r"F0W\d", "BSWF"),                # Wide Fine
    (r"FQ\d+W", "BSWF"),               # Wide Fine Quad-Pol
    (r"FQ\d+", "BSF"),                 # Fine Quad-Pol
    (r"F\d+[NF]?", "BSF"),             # Fine
    (r"SQ\d+W", "BSW"),                # Wide Standard Quad-Pol
    (r"SQ\d+", "BS"),                  # Standard Quad-Pol
    (r"W\d", "BSW"),                   # Wide
    (r"S\d", "BS"),                    # Standard
    (r"E[HL]\d", "BS"),                # Extended High / Low
)

# operationalMode -> <TTTTTTTTTT> mode field (4 chars, "_" padded)
MODE_FIELD = {
    "BS": "BS__", "BSF": "BSF_", "BSW": "BSW_", "BSWF": "BSWF",
    "ML": "ML__", "MLW": "MLW_", "SL": "SL__",
}
# native product type -> (processingLevel, processedLevel code)
LEVELS = {
    "SLC": ("1", "L1"), "SGF": ("1", "L1"), "SGX": ("1", "L1"),
    "SSG": ("2", "L2"), "SPG": ("2", "L2"),
    "SCN": ("1", "L1"), "SCW": ("1", "L1"), "SCF": ("1", "L1"), "SCS": ("1", "L1"),
}
SCANSAR_MODES = ("SCN", "SCW")


def _typecodes():
    """(native product type, operationalMode) -> product type, spec Table 2."""
    table = {}
    for mode, field in MODE_FIELD.items():
        for native in ("SLC", "SGF", "SGX", "SSG", "SPG"):
            table[(native, mode)] = "L%s_%s%s" % (LEVELS[native][0], field, native)
    for mode in SCANSAR_MODES:
        # the ScanSAR product named after its mode is the plain one
        table[(mode, mode)] = "L1_%s____" % mode
        table[("SCF", mode)] = "L1_%s_SCF" % mode
        table[("SCS", mode)] = "L1_%s_SCS" % mode
    return table


TYPECODE_MAP = _typecodes()

# polarisationMode allowed per operationalMode (spec Table 2)
POLARISATION_MODES = {
    "BS": "SDQ", "BSF": "SDQ", "BSW": "SDQ", "BSWF": "SDQ",
    "ML": "S", "MLW": "S", "SL": "S",
    "SCN": "SD", "SCW": "SD",
}

# polarisationChannels values the EOPF-EOS schema accepts (", " separated,
# fixed channel order): the native channels are matched as a set
ALLOWED_POLARISATION_CHANNELS = (
    "HH", "HV", "VH", "VV",
    "HH, VV", "HH, VH", "HH, HV", "VH, VV", "VH, HV", "VV, HV", "VV, VH",
    "HV, VH",
    "HH, HV, VH, VV",
)

# measurements link media type, by image file extension
MEDIA_TYPES = {
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    # NITF: no media type in the schema link-types thesaurus
    ".ntf": "application/octet-stream",
}

WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"
EPSG_URI = "http://www.opengis.net/def/crs/EPSG/0/%d"

SPEED_OF_LIGHT = 299792458.0
EARTH_RADIUS = 6371000.0


def format_utc(value):
    """datetime -> RFC 3339 with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    return "%s.%03dZ" % (value.strftime("%Y-%m-%dT%H:%M:%S"), value.microsecond // 1000)


def parse_utc(text):
    """'2010-05-27T23:16:08.123456Z' -> datetime (UTC; fraction cut to
    microseconds)."""
    match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$", (text or "").strip())
    if not match:
        raise Exception("unexpected RADARSAT-2 time format: '%s'" % text)
    value = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
    if match.group(2):
        value = value.replace(microsecond=int((match.group(2) + "000000")[:6]))
    return value


def operational_mode(beam_mnemonic):
    for pattern, mode in MODE_RULES:
        if re.fullmatch(pattern, beam_mnemonic):
            return mode
    raise Exception("unsupported RADARSAT-2 beam mode: '%s'" % beam_mnemonic)


def polarisation_channels(channels):
    """Native channel list -> the schema value with the same channels."""
    wanted = set(channels)
    for value in ALLOWED_POLARISATION_CHANNELS:
        allowed = value.split(", ")
        if len(allowed) == len(channels) and set(allowed) == wanted:
            return value
    raise Exception("polarisation channels %s not allowed by the schema"
                    % ",".join(channels))


def _strip_namespaces(root):
    for element in root.iter():
        if isinstance(element.tag, str) and element.tag.startswith("{"):
            element.tag = element.tag.split("}", 1)[1]
    return root


class Product_Radarsat2(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        if os.path.basename(str(self.path)).lower() != ENTRY_NAME:
            raise Exception("not a RADARSAT-2 product annotation (%s): %s" % (ENTRY_NAME, path))

        self.EO_FOLDER = os.path.dirname(self.path)
        self.productName = os.path.basename(os.path.normpath(self.EO_FOLDER))
        self.preview_path = None
        self.tmpSize = 0

        self.root = _strip_namespaces(ET.parse(self.path).getroot())
        if self.root.tag != "product":
            raise Exception("not a RADARSAT-2 product annotation: %s" % path)

        if self.debug != 0:
            print(" init class Product_Radarsat2")

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

    def image_files(self):
        """Image files relative to the product folder, in annotation order."""
        files = [e.text.strip() for e in self.root.findall("imageAttributes/fullResolutionImageData")
                 if e.text and e.text.strip()]
        if not files:
            raise Exception("no fullResolutionImageData in %s" % self.path)
        return files

    def browse_file(self):
        path = os.path.join(self.EO_FOLDER, BROWSE_NAME)
        if not os.path.isfile(path):
            raise FileNotFoundError("corrupt RADARSAT-2 native product (no %s): %s"
                                    % (BROWSE_NAME, self.EO_FOLDER))
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
        product.xml in place. Walk the product folder to get the size of what
        lands in measurements/."""
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
        native = self.text("imageGenerationParameters/generalProcessingInformation/productType").upper()
        beam = self.text("sourceAttributes/beamModeMnemonic")
        mode = operational_mode(beam)
        typecode = TYPECODE_MAP.get((native, mode))
        if typecode is None:
            raise Exception("unsupported RADARSAT-2 product: %s in beam mode '%s' (%s)"
                            % (native, beam, mode))
        level, level_code = LEVELS[native]

        self.metadata.setMetadataPair(NATIVE_PRODUCT_TYPE, native)
        self.metadata.setMetadataPair(BEAM_MODE, beam)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        print(("TYPECODE SET TO: %s (product %s, beam %s)" % (typecode, native, beam)))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met

        satellite = self.text("sourceAttributes/satellite")
        if satellite != "RADARSAT-2":
            raise Exception("not a RADARSAT-2 product: satellite '%s'" % satellite)

        # sensing times: zero Doppler time of the first / last image line
        sar = "imageGenerationParameters/sarProcessingInformation/"
        first = parse_utc(self.text(sar + "zeroDopplerTimeFirstLine"))
        last = parse_utc(self.text(sar + "zeroDopplerTimeLastLine"))
        start, stop = format_utc(min(first, last)), format_utc(max(first, last))
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, format_utc(parse_utc(
            self.text("imageGenerationParameters/generalProcessingInformation/processingTime"))))

        # package creation date (spec Table 7): now, the conversion time
        created = format_utc(datetime.now(timezone.utc))
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # orbit
        orbit_info = "sourceAttributes/orbitAndAttitude/orbitInformation/"
        direction = self.text(orbit_info + "passDirection").upper()
        if direction not in ("ASCENDING", "DESCENDING"):
            raise Exception("invalid pass direction: '%s'" % direction)
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, direction)
        orbit = self.orbit_number()
        if orbit is not None:
            met.setMetadataPair(metadata.METADATA_ORBIT, orbit)
        else:
            # keep the cfg METADATA_ORBIT fallback, as the legacy converter did
            print(("WARNING: no orbit number in %s (orbit data file / .prodReport):"
                   " cfg METADATA_ORBIT used" % self.EO_FOLDER))

        # polarisation (spec Tables 2 and 11)
        channels = self.text("sourceAttributes/radarParameters/polarizations").split()
        mode_letter = {1: "S", 2: "D", 4: "Q"}.get(len(channels))
        if mode_letter is None:
            raise Exception("unsupported polarisation list: %s" % channels)
        met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, mode_letter)
        met.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, polarisation_channels(channels))

        look = self.text("sourceAttributes/radarParameters/antennaPointing").upper()
        if look not in ("RIGHT", "LEFT"):
            raise Exception("invalid antenna pointing: '%s'" % look)
        met.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, look)

        self.buildTypeCode(processInfo)
        mode = met.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if mode_letter not in POLARISATION_MODES[mode]:
            raise Exception("polarisation mode %s not allowed for operational mode %s (spec Table 2)"
                            % (mode_letter, mode))
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def orbit_number(self):
        """Orbit number: leading number of the orbit data file name
        (e.g. '23861_DEF.ORB'), else the 'Orbit Number' line of a .prodReport
        in the product folder, else None."""
        orbit_file = self.root.findtext("sourceAttributes/orbitAndAttitude/orbitInformation/orbitDataFile")
        match = re.match(r"^\s*(\d+)_", orbit_file or "")
        if match:
            return int(match.group(1))
        for name in sorted(os.listdir(self.EO_FOLDER)):
            if not name.endswith(PROD_REPORT_SUFFIX):
                continue
            with open(os.path.join(self.EO_FOLDER, name), encoding="utf-8", errors="replace") as fd:
                for line in fd:
                    match = re.match(r"^\s*Orbit Number\s*:\s*(\d+)\s*$", line)
                    if match:
                        return int(match.group(1))
        return None

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the native product size; the base pipeline
        # would fill the eoSIP size here, so mark it as ICEYE does
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        sar = "imageGenerationParameters/sarProcessingInformation/"
        near = self.float_value(sar + "incidenceAngleNearRange")
        far = self.float_value(sar + "incidenceAngleFarRange")
        incidence = round((near + far) / 2.0, 3)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, incidence)

        range_resolution, azimuth_resolution = self.resolutions(incidence)
        resolution = round(max(range_resolution, azimuth_resolution), 3)
        met.addLocalAttribute("rangeResolution", range_resolution)
        met.addLocalAttribute("azimuthResolution", azimuth_resolution)
        # single figure the spec also asks for: worst of the two directions
        met.addLocalAttribute("resolution", resolution)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)

        met.addLocalAttribute("referenceSystemIdentifier", self.reference_system())

        # the measurements link points at the first image file, inside the
        # product folder that measurements/ holds
        image = self.image_files()[0]
        extension = os.path.splitext(image)[1].lower()
        if extension not in MEDIA_TYPES:
            raise Exception("unsupported image file: %s" % image)
        met.addLocalAttribute("nativeDataFile", "%s/%s" % (self.productName, image))
        met.addLocalAttribute("measurementsMediaType", MEDIA_TYPES[extension])

        print(("## resolution range=%s azimuth=%s; incidence=%s"
               % (range_resolution, azimuth_resolution, incidence)))

    def resolutions(self, incidence):
        """Ground range and azimuth resolution (m), from the processed look
        bandwidths (product.xml gives no resolution figure):
        range = c / (2 B_range sin(incidence)), azimuth = V_ground / B_azimuth,
        V_ground the state vector speed scaled down to the ground."""
        sar = "imageGenerationParameters/sarProcessingInformation/"
        range_bandwidth = self.float_value(sar + "rangeLookBandwidth")
        azimuth_bandwidth = self.float_value(sar + "azimuthLookBandwidth")
        height = self.float_value(sar + "satelliteHeight")
        vector = self.root.find("sourceAttributes/orbitAndAttitude/orbitInformation/stateVector")
        if vector is None:
            raise Exception("no orbit state vector in %s" % self.path)
        speed = math.sqrt(sum(self.float_value(axis, vector) ** 2
                              for axis in ("xVelocity", "yVelocity", "zVelocity")))
        if range_bandwidth <= 0 or azimuth_bandwidth <= 0 or speed <= 0:
            raise Exception("invalid look bandwidth / velocity in %s" % self.path)
        ground_speed = speed * EARTH_RADIUS / (EARTH_RADIUS + height)
        range_resolution = SPEED_OF_LIGHT / (2.0 * range_bandwidth * math.sin(math.radians(incidence)))
        azimuth_resolution = ground_speed / azimuth_bandwidth
        return round(range_resolution, 3), round(azimuth_resolution, 3)

    def reference_system(self):
        """CRS URI: the UTM zone of a map image (SSG / SPG), WGS84 geographic
        for the others (their geolocation grid is geodetic)."""
        projection = self.root.find("imageAttributes/geographicInformation/mapProjection")
        if projection is None:
            return WGS84
        ellipsoid = re.sub(r"[\s_-]", "", self.text(
            "imageAttributes/geographicInformation/referenceEllipsoidParameters/ellipsoidName")).upper()
        if ellipsoid not in ("WGS84", "WGS1984"):
            raise Exception("unsupported ellipsoid '%s' in %s" % (ellipsoid, self.path))
        utm = projection.find("utmProjectionParameters")
        if utm is None:
            raise Exception("unsupported map projection '%s' in %s"
                            % (projection.findtext("mapProjectionDescriptor"), self.path))
        zone = int(self.text("utmZone", utm))
        if not 1 <= zone <= 60:
            raise Exception("invalid UTM zone %d in %s" % (zone, self.path))
        hemisphere = self.text("hemisphere", utm).upper()
        if hemisphere not in ("NORTH", "SOUTH"):
            raise Exception("invalid UTM hemisphere '%s' in %s" % (hemisphere, self.path))
        return EPSG_URI % ((32600 if hemisphere == "NORTH" else 32700) + zone)

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint posList (lat lon pairs, CCW) from the four corner tie
        points of the geolocation grid (first / last line x first / last
        pixel)."""
        points = {}
        for tie in self.root.findall("imageAttributes/geographicInformation/geolocationGrid/imageTiePoint"):
            line = self.float_value("imageCoordinate/line", tie)
            pixel = self.float_value("imageCoordinate/pixel", tie)
            points[(line, pixel)] = (self.float_value("geodeticCoordinate/latitude", tie),
                                     self.float_value("geodeticCoordinate/longitude", tie))
        if len(points) < 4:
            raise Exception("expected a geolocation grid of at least 4 tie points in %s" % self.path)
        lines = [line for line, _ in points]
        pixels = [pixel for _, pixel in points]
        corners = [(min(lines), min(pixels)), (min(lines), max(pixels)),
                   (max(lines), max(pixels)), (max(lines), min(pixels))]
        if any(corner not in points for corner in corners):
            raise Exception("geolocation grid without its 4 corner tie points in %s" % self.path)
        ring = [points[corner] for corner in corners] + [points[corners[0]]]
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
