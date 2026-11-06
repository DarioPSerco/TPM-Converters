"""This class represents a Beijing-1 / NigeriaSat-1 / UK-DMC-1 (SLIM6) native
product, per "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1 and
UK-DMC-1 products" 1.0.

The delivery is a flat .zip (unpacked by run_mission.py into a <zip stem>/
folder) holding one DIMAP product:

- <dataset>.dim        DIMAP header, entry file of the product (cfg [Search])
- <dataset>.tif        GeoTIFF image
- <dataset>_ql.jpg     quicklook, named by the .dim DATASET_QL_PATH
- <dataset>_meta.sip   zip with repository.xml (resolution), in L1R products
                       also an overview TIFF
- <dataset>.htm/.xsl   rendering of the .dim (not read)

One delivery = one EOPF-EOS product. The whole unzipped folder is the native
product (measurements/, spec section 3); the quicklook JPEG is the overview
(spec section 4), re-encoded as PNG by package_dmc_zips.

Supported product types (spec Table 2): L1_OPT_MS_ (native level L1R) and
L1_ORT_MS_ (native level L1T), instrument SLIM6, operationalMode MS3B.

Read from the .dim: platform, level, sensing time, footprint, sun angles, CRS,
production date; from repository.xml in the _meta.sip: resolution and cloud
cover (when filled). Every value is taken as delivered. The <bbvv> counter of
the package name is not read here: name_registry assigns it, keyed by the
.dim DATASET_NAME (dataset_name).

A reduced-resolution QL product (GEOMETRIC_PROCESSING 1T_QL_..., e.g. 320 m)
has the same structure and is converted like any other product.

SCENE_CENTER_TIME carries no time zone; it is UTC: repository.xml stores the
same instant as a Unix time (ms).
"""
import os
import zipfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

DIM_EXTENSION = ".dim"
SIP_SUFFIX = "_meta.sip"
REPOSITORY_XML = "repository.xml"

# custom metadata keys
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# <MMM> package prefix -> (2-digit alias, platform id, platformShortName)
# (spec Tables 1 and 8)
PLATFORMS = {
    'BJ1': ('BJ', '1', 'Beijing-1'),
    'NG1': ('NG', '1', 'NigeriaSat-1'),
    'UK1': ('UK', '1', 'UK-DMC-1'),
}
# .dim MISSION -> <MMM> prefix; an unknown MISSION fails the conversion
NATIVE_PLATFORMS = {
    'BEIJING': 'BJ1',
    'NIGERIASAT': 'NG1',
    'UK-DMC': 'UK1',
}
# MISSION_INDEX is optional (absent in the NigeriaSat-1 / UK-DMC-1 samples);
# when present it must be 1: the spec covers only the -1 satellites
NATIVE_MISSION_INDEX = '1'
# .dim INSTRUMENT values accepted as SLIM6
NATIVE_INSTRUMENTS = ('SLIM-6',)

# native level (spec Table 17 processedLevel code) -> product type (Table 2)
PRODUCT_TYPES = {
    'L1R': 'L1_OPT_MS_',
    'L1T': 'L1_ORT_MS_',
}
# .dim GEOMETRIC_PROCESSING, part before '_' -> L1R / L1T (after it: region,
# e.g. 1R_FI, or QL / CRS / region, e.g. 1T_EPSG_4258_FI, 1T_QL_EPSG_2393_FI)
NATIVE_LEVELS = {
    '1R': 'L1R',
    '1T': 'L1T',
}

# spec Tables 9, 10, 16
INSTRUMENT = 'SLIM6'
OPERATIONAL_MODE = 'MS3B'
PROCESSING_LEVEL = '1'

# spec Table 14, in metres: band (start, end) per spectral range
SPECTRAL_RANGES = {
    'VIS': [(520e-9, 600e-9), (630e-9, 690e-9)],
    'NIR': [(770e-9, 900e-9)],
}


def wavelengths():
    """spec Table 13 / 14: one entry per spectral range, start / end the
    outer bounds of its bands, discreteWavelengths the band means."""
    out = []
    for name, bands in SPECTRAL_RANGES.items():
        out.append({
            "spectralRange": name,
            "startWavelength": min(b[0] for b in bands),
            "endWavelength": max(b[1] for b in bands),
            "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
        })
    return out


def format_utc(value):
    """datetime -> RFC 3339 UTC with milliseconds, YYYY-MM-DDThh:mm:ss.sssZ
    (spec Table 6), used for every datetime."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (value.microsecond // 1000)


def crs_uri(epsg_code):
    """EPSG code -> referenceSystemIdentifier URI (spec Table 15)."""
    code = int(epsg_code)
    if code <= 0:
        raise Exception("invalid EPSG code: %s" % epsg_code)
    return "http://www.opengis.net/def/crs/EPSG/0/%d" % code


def closed_ccw_ring(points):
    """[(lon, lat), ...] -> closed, counter-clockwise GeoJSON ring (spec
    section 5.1.1, RFC 7946); raises on a degenerate footprint."""
    ring = [[float(p[0]), float(p[1])] for p in points]
    if len(ring) < 3:
        raise Exception("degenerate footprint: %d point(s)" % len(ring))
    if ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    # shoelace on lon/lat: positive area = counter-clockwise
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    if area == 0:
        raise Exception("degenerate footprint: zero area")
    if area < 0:
        ring.reverse()
    return ring


def _text(root, path, required=True):
    """Stripped text of the first element at path, None when absent / empty
    and not required."""
    value = root.findtext(path)
    value = value.strip() if value else None
    if required and not value:
        raise Exception("missing in the .dim: %s" % path)
    return value


def dim_quicklook(dim_path):
    """The quicklook JPEG named by the .dim DATASET_QL_PATH, next to it (same
    rule as the packager)."""
    root = ET.parse(dim_path).getroot()
    node = root.find("Dataset_Id/DATASET_QL_PATH")
    href = node.get("href") if node is not None else None
    if not href:
        raise Exception("no Dataset_Id/DATASET_QL_PATH in %s" % dim_path)
    path = os.path.join(os.path.dirname(dim_path), href)
    if not os.path.isfile(path):
        raise Exception("quicklook %s named by %s not found" % (href, os.path.basename(dim_path)))
    return path


def parse_dim_datetime(value):
    """.dim 'YYYY-MM-DD hh:mm:ss' -> datetime, UTC (see the module
    docstring)."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def frame_points(root):
    """Dataset_Frame corners as (lon, lat) in degrees: FRAME_LON / FRAME_LAT
    when present (projected products also carry FRAME_X / FRAME_Y in
    metres), else FRAME_X / FRAME_Y when their unit is DEG; fails otherwise.
    The degrees are used as delivered, without coordinate conversion."""
    points = []
    for v in root.findall("Dataset_Frame/Vertex"):
        if v.find("FRAME_LON") is not None:
            points.append((v.findtext("FRAME_LON"), v.findtext("FRAME_LAT")))
            continue
        x, y = v.find("FRAME_X"), v.find("FRAME_Y")
        if x is None or y is None or x.get("unit") != "DEG" or y.get("unit") != "DEG":
            raise Exception("Dataset_Frame vertex without degrees (FRAME_LON / "
                            "FRAME_LAT, or FRAME_X / FRAME_Y in DEG)")
        points.append((x.text, y.text))
    return points


def read_repository(sip_path):
    """GeoImage values of repository.xml inside the _meta.sip:
    (resolution or None, cloud cover percent or None)."""
    with zipfile.ZipFile(sip_path) as zf:
        if REPOSITORY_XML not in zf.namelist():
            raise Exception("no %s in %s" % (REPOSITORY_XML, os.path.basename(sip_path)))
        root = ET.fromstring(zf.read(REPOSITORY_XML))
    images = [o for o in root.iter("OBJECT") if o.get("type") == "GeoImage"]
    if len(images) != 1:
        raise Exception("expected one GeoImage in %s, found %d" % (REPOSITORY_XML, len(images)))
    resolution = _text(images[0], "Resolution", required=False)
    cloud = _text(images[0], "CloudCoverPercent", required=False)
    return resolution, cloud


class Product_DMC(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        name = os.path.basename(self.path)
        if not name.lower().endswith(DIM_EXTENSION):
            raise Exception("not a DIMAP header (%s): %s" % (DIM_EXTENSION, path))
        self.dim_name = name
        # .dim DATASET_NAME, read by extractMetadata: the name_registry key
        self.dataset_name = None
        # the unzipped delivery folder: the native product unit
        self.EO_FOLDER = os.path.dirname(self.path)
        self.browse_path = None
        self.tmpSize = 0
        if self.debug != 0:
            print(" init class Product_DMC (%s)" % self.EO_FOLDER)

    # -- product lifecycle ------------------------------------------------

    def afterProductDone(self):
        pass

    def getMetadataInfo(self):
        pass

    # JSON-only mode: no eoSIP browse; the packager re-encodes the
    # quicklook JPEG as the overview PNG.
    def makeBrowses(self, processInfo):
        pass

    def extractToPath(self, folder=None, dont_extract=False):
        """No extraction to disk is needed. Check the quicklook exists (so no
        manifest is written for a product the packager would reject) and sum
        the size of the delivery, which is what lands in measurements/ (spec
        Table 15 size)."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        self.EXTRACTED_PATH = folder
        self.browse_path = dim_quicklook(self.path)
        self.contentList = []
        self.tmpSize = 0
        for root, dirs, files in os.walk(self.EO_FOLDER):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(root, name)
                self.contentList.append(os.path.relpath(path, self.EO_FOLDER).replace(os.sep, "/"))
                self.tmpSize += os.stat(path).st_size
        print((" #### native delivery %s: %d file(s), %d bytes, browse %s"
               % (os.path.basename(self.EO_FOLDER), len(self.contentList), self.tmpSize,
                  os.path.basename(self.browse_path))))

    # -- metadata ---------------------------------------------------------

    def set_platform(self, prefix):
        """Platform values from a <MMM> prefix: names the package and the
        manifest platform (spec Tables 1, 8)."""
        if prefix not in PLATFORMS:
            raise Exception("unsupported platform prefix: '%s'" % prefix)
        alias, platform_id, short_name = PLATFORMS[prefix]
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, alias)
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform_id)
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, short_name)
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, INSTRUMENT)

    def set_level(self, level):
        """Product type, processing level and processed level code from the
        native level L1R / L1T (spec Tables 2, 16, 17)."""
        if level not in PRODUCT_TYPES:
            raise Exception("unsupported native level: '%s'" % level)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, PRODUCT_TYPES[level])
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, PROCESSING_LEVEL)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, OPERATIONAL_MODE)

    def set_sensing_time(self, value):
        """Beginning = ending sensing time: the .dim has the scene centre
        time only (spec Table 11: no ending time -> the beginning time).
        Also the EO name date tokens."""
        stamp = format_utc(value)
        date, time = stamp[:-1].split("T")
        for key, val in ((metadata.METADATA_START_DATE_TIME, stamp),
                         (metadata.METADATA_STOP_DATE_TIME, stamp),
                         (metadata.METADATA_START_DATE, date),
                         (metadata.METADATA_START_TIME, time),
                         (metadata.METADATA_STOP_DATE, date),
                         (metadata.METADATA_STOP_TIME, time)):
            self.metadata.setMetadataPair(key, val)

    def extractMetadata(self, met=None, processInfo=None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met
        # package creation date (spec Table 6): now, the conversion time
        created = format_utc(datetime.now(timezone.utc))
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        root = ET.parse(self.path).getroot()
        scene = "Dataset_Sources/Source_Information/Scene_Source/"

        mission = _text(root, scene + "MISSION")
        if mission not in NATIVE_PLATFORMS:
            raise Exception("unsupported MISSION: %s" % mission)
        index = _text(root, scene + "MISSION_INDEX", required=False)
        if index is not None and index != NATIVE_MISSION_INDEX:
            raise Exception("unsupported MISSION_INDEX %s for MISSION %s" % (index, mission))
        self.set_platform(NATIVE_PLATFORMS[mission])
        instrument = _text(root, scene + "INSTRUMENT")
        if instrument not in NATIVE_INSTRUMENTS:
            raise Exception("unsupported INSTRUMENT: %s" % instrument)

        geometric = _text(root, "Data_Processing/GEOMETRIC_PROCESSING")
        code = geometric.split("_")[0]
        if code not in NATIVE_LEVELS:
            raise Exception("unsupported GEOMETRIC_PROCESSING: %s" % geometric)
        self.set_level(NATIVE_LEVELS[code])

        self.dataset_name = _text(root, "Dataset_Id/DATASET_NAME")

        self.set_sensing_time(parse_dim_datetime(
            _text(root, "Data_Strip/Sensor_Configuration/Time_Stamp/SCENE_CENTER_TIME")))

        met.addLocalAttribute("footprintRing", closed_ccw_ring(frame_points(root)))

        # mandatory (spec Table 12)
        met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, float(_text(root, scene + "SUN_AZIMUTH")))
        met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, float(_text(root, scene + "SUN_ELEVATION")))
        # VIEWING_ANGLE is not mapped: the .dim does not say whether it is
        # along or across track, so both incidence angles are left out.

        # CRS only when declared (spec Table 15)
        crs = _text(root, "Coordinate_Reference_System/Horizontal_CS/HORIZONTAL_CS_CODE", required=False)
        if crs:
            authority, _, code = crs.partition(":")
            if authority.upper() != "EPSG":
                raise Exception("unsupported HORIZONTAL_CS_CODE: %s" % crs)
            met.addLocalAttribute("referenceSystemIdentifier", crs_uri(code))

        # processing date (spec Table 16): the .dim production date (a day)
        produced = _text(root, "Production/DATASET_PRODUCTION_DATE")
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME,
                            format_utc(datetime.strptime(produced, "%Y-%m-%d")))

        # resolution (mandatory, spec Table 10) and cloud cover (written only
        # when filled, percent) are only in repository.xml of the _meta.sip
        sip = os.path.join(self.EO_FOLDER, self.dim_name[:-len(DIM_EXTENSION)] + SIP_SUFFIX)
        if not os.path.isfile(sip):
            raise Exception("%s not found next to %s" % (os.path.basename(sip), self.dim_name))
        resolution, cloud = read_repository(sip)
        if not resolution:
            raise Exception("no GeoImage Resolution in %s" % os.path.basename(sip))
        met.setMetadataPair(metadata.METADATA_RESOLUTION, float(resolution))
        if cloud:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, float(cloud))
        # orbitNumber / orbitDirection (optional, spec 5.1.2.3.2) are not
        # written: the spec names no native source and none of the sample
        # deliveries (.dim or repository.xml) carries them

    def extractQuality(self, helper, met):
        pass

    def toString(self):
        return "path:%s" % self.path

    def dump(self):
        print(self.toString())
