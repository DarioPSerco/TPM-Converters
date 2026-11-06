# -*- coding: cp1252 -*-
#
# this class represent a GEOSAT (ex Deimos) product: the DIMAP delivery ZIP
#
# The ZIP holds one DIMAP document (.dim) per product, or one per component
# (PAN + MS4 for a bundle, two views for a stereo pair), next to the GeoTIFF
# image(s) and their quicklook(s). A bundle / stereo pair described by a
# single .dim is split by its image files. Every component gets one
# acquisitionParameters entry, one measurements link and one overview
# ("EOPF-EOS Specialization for GEOSAT products" 1.01).
#
# GEOSAT-1 (ex Deimos-1, SLIM6):  DE01_SL6_22P_1T_<start>_<stop>_...
# GEOSAT-2 (ex Deimos-2, HiRAIS): DE2_PM4_L1C_000000_<start>_<stop>_DE2_<orbit>_<id>
#
import os
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.product_directory import Product_Directory

# custom metadata keys (mission-local, like PNEO's)
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# spec Tables 9 / 10: platform index -> (platformShortName, instrumentShortName)
PLATFORMS = {'1': ('GEOSAT-1', 'SLIM6'), '2': ('GEOSAT-2', 'HiRAIS')}

# native product name -> (platform index, mode, level)
GEOSAT1_NAME = re.compile(r'^DE0?1_SL6_(22[PST])_L?([12][RT])(?:_|$)', re.IGNORECASE)
GEOSAT2_NAME = re.compile(r'^DE0?2_([A-Z0-9]{3})_L?(1[BCD])(?:_|$)', re.IGNORECASE)
# image / quicklook file name -> GEOSAT-2 spectral mode (DE2_<mode>_...)
GEOSAT2_FILE_MODE = re.compile(r'^DE0?2_([A-Z0-9]{3})_', re.IGNORECASE)
# orbit number in a GEOSAT-2 name: ..._DE2_<orbit>_<id>
NAME_ORBIT = re.compile(r'_DE0?[12]_(\d+)_[0-9A-Z]+$', re.IGNORECASE)

# native spectral mode -> component kind. GEOSAT-1 banks P / S / P+S merge
# (22P / 22S / 22T) are all the 3-band MS3 kind. GEOSAT-2 PS3 (3-band
# pansharpened) has no product type nor wavelength table in the
# specialization (PSH is four-band, Table 3): rejected.
KINDS = {'22P': 'MS3', '22S': 'MS3', '22T': 'MS3',
         'PAN': 'PAN', 'MS4': 'MS', 'PSH': 'PSH', 'PS4': 'PSH'}
# multi-component native modes
BUNDLE_MODE = 'PM4'
STEREO_MODE = 'STP'

# spec Tables 2 / 3 (and section 1.1): (platform, kind, native level) -> product type.
# Table 3 spells the L1C pansharpened type L1CRPC_PSH and the L1D one
# L1DORT_PSH; section 1.1 spells them L1CORT_PSH / L1DORTEPSH, which follow
# the other types' pattern (L1CORT_PAN, L1DORTEBDL): section 1.1 is used.
PRODUCT_TYPES = {
    ('1', 'MS3', '1R'): 'L1_GEO_MS_',
    ('1', 'MS3', '1T'): 'L1_ORT_MS_',
    ('1', 'MS3', '2T'): 'L2_ORT_MS_',
    ('2', 'PAN', '1B'): 'L1BORTRPAN',
    ('2', 'PAN', '1C'): 'L1CORT_PAN',
    ('2', 'MS', '1B'): 'L1BORTRMS_',
    ('2', 'MS', '1C'): 'L1CORT_MS_',
    ('2', 'PSH', '1B'): 'L1BORTRPSH',
    ('2', 'PSH', '1C'): 'L1CORT_PSH',
    ('2', 'PSH', '1D'): 'L1DORTEPSH',
    ('2', 'BDL', '1B'): 'L1BORTRBDL',
    ('2', 'BDL', '1C'): 'L1CORT_BDL',
    ('2', 'BDL', '1D'): 'L1DORTEBDL',
}
# stereo pairs (spec Table 3), whatever the native level
STEREO_TYPES = {'PAN': 'SYNSTERPAN', 'PSH': 'SYNSTERPSH'}

# native level -> (processingLevel (allowed values 0 / 1 / 1A / 1B / 1C /
# 1D / 2 / 2A / 2B / 2C / 3 / SYN, bare codes without the L prefix), native
# processedLevel code (spec Table 20, L-prefixed)). GEOSAT-1 1R / 1T are
# level 1 products (L1_*), 2T the level 2 one (L2_*) whose native level is
# L2T.
LEVELS = {'1R': ('1', 'L1'), '1T': ('1', 'L1'), '2T': ('2', 'L2T'),
          '1B': ('1B', 'L1B'), '1C': ('1C', 'L1C'), '1D': ('1D', 'L1D')}
STEREO_LEVEL = 'SYN'
# levels whose product is orthorectified, so geo-referenced: the CRS is
# mandatory (spec Table 18)
ORTHO_LEVELS = {'1T', '2T', '1C', '1D'}

# spec Table 11 / Tables 2-3: operational mode of each component kind. Table 3
# writes M4B for the pansharpened types, not one of Table 11's allowed
# values: MS4B is used. Bundle components are MS (Table 3 and the bundle
# example), stereo PSH pairs too.
OPERATIONAL_MODE = {'MS3': 'MS3B', 'PAN': 'PAN', 'MS': 'MS4B', 'PSH': 'MS4B'}
BUNDLE_OPERATIONAL_MODE = 'MS'
STEREO_OPERATIONAL_MODE = {'PAN': 'PAN', 'PSH': 'MS'}

# spec Tables 16 (non-bundle, by operational mode) / 17 (bundle), in metres:
# per kind, one (spectralRange, start, end) per row. discreteWavelengths is
# the mean of the row's range (Table 15). Table 17's five bundle rows are
# split between the MS (four VIS / IR rows) and the PAN (VNIR row)
# component; the values are the same as Table 16's.
SPECTRAL_RANGES = {
    'MS3': (('VIS', 520e-09, 600e-09), ('VIS', 630e-09, 690e-09), ('IR', 770e-09, 900e-09)),
    'PAN': (('VNIR', 560e-09, 900e-09),),
    'MS': (('VIS', 466e-09, 525e-09), ('VIS', 532e-09, 599e-09),
           ('VIS', 640e-09, 697e-09), ('IR', 770e-09, 892e-09)),
}
SPECTRAL_RANGES['PSH'] = SPECTRAL_RANGES['MS']

# spec Tables 2 / 3 nominal resolution (m), used when the DIMAP document
# carries none (and for the components of a bundle split from one document)
NOMINAL_RESOLUTION = {
    ('MS3', '1R'): 22.0, ('MS3', '1T'): 22.0, ('MS3', '2T'): 22.0,
    ('PAN', '1B'): 1.0, ('PAN', '1C'): 0.75, ('PAN', '1D'): 0.4,
    ('MS', '1B'): 4.0, ('MS', '1C'): 3.0, ('MS', '1D'): 1.6,
    ('PSH', '1B'): 1.0, ('PSH', '1C'): 0.75, ('PSH', '1D'): 0.4,
}
STEREO_RESOLUTION = 1.0

# bundle components in the example's order (MS first), with their overview
# suffix; stereo views keep the delivery order
BUNDLE_ORDER = ('MS', 'PAN')
BUNDLE_PREVIEW_SUFFIX = {'MS': '_MS', 'PAN': '_PAN'}

IMAGE_EXT = ('.TIF', '.TIFF')
QUICKLOOK_EXT = ('.PNG', '.JPG', '.JPEG')
OVERVIEW_MAX_SIZE = 1000

# Quality_Parameter codes (DEIMOS-IMAGING:* on older products, GEOSAT:* on
# newer ones; SPACEMETRIC:HEADING on GEOSAT-1)
ORBIT_DIRECTION_CODES = ('DEIMOS-IMAGING:ORD', 'GEOSAT:ORD', 'SPACEMETRIC:HEADING')
CLOUD_COVER_CODES = ('DEIMOS-IMAGING:CCP', 'GEOSAT:CCP')
DIRECTIONS = {'A': 'ASCENDING', 'D': 'DESCENDING',
              'ASCENDING': 'ASCENDING', 'DESCENDING': 'DESCENDING'}


def normalise_utc(value):
    """DIMAP datetime (UTC, with or without 'Z' / fraction) -> RFC 3339 UTC
    with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?(?:Z|[+-]00:?00)?$",
                     str(value).strip())
    if not match:
        raise Exception("unexpected GEOSAT datetime format: '%s'" % value)
    date, time, frac = match.groups()
    return "%sT%s.%sZ" % (date, time, (frac or "").ljust(3, "0")[:3])


def production_utc(value):
    """DATASET_PRODUCTION_DATE -> RFC 3339 UTC. GEOSAT-1 deliveries give the
    date only: the time is not known and is written as midnight. Acquisition
    times stay strict (normalise_utc)."""
    if value is not None and re.match(r"^\d{4}-\d{2}-\d{2}$", str(value).strip()):
        value = "%sT00:00:00" % str(value).strip()
    return normalise_utc(value)


def mission_index_agrees(mission_index, mission, platform):
    """MISSION_INDEX against the platform of the product name. GEOSAT-2
    deliveries name their mission 'Deimos 2' and number it 0001 within it."""
    index = mission_index.strip().lstrip('0')
    if index == platform:
        return True
    return platform == '2' and index == '1' and 'DEIMOS 2' in (mission or '').upper()


def wavelengths(kind):
    """spec Table 16 / 17 rows of the component kind: one entry per row,
    discreteWavelengths the mean of its range."""
    return [{
        "spectralRange": name,
        "startWavelength": start,
        "endWavelength": end,
        "discreteWavelengths": [round((start + end) / 2, 12)],
    } for name, start, end in SPECTRAL_RANGES[kind]]


def crs_uri(code):
    """DIMAP CRS code (EPSG:32630, urn:ogc:def:crs:EPSG::32630, 32630) ->
    the OGC http URI the spec asks for
    (http://www.opengis.net/def/crs/EPSG/0/32630)."""
    code = (code or '').strip()
    for pattern in (r"^urn:ogc:def:crs:EPSG:[^:]*:(\d+)$", r"^EPSG:+(\d+)$", r"^(\d+)$"):
        match = re.match(pattern, code, re.IGNORECASE)
        if match:
            return "http://www.opengis.net/def/crs/EPSG/0/%s" % match.group(1)
    return None


def wkt_epsg(wkt):
    """EPSG code of a WKT CRS: its outermost AUTHORITY (the last one)."""
    found = re.findall(r'AUTHORITY\[\s*"EPSG"\s*,\s*"(\d+)"\s*\]', wkt or '')
    return found[-1] if found else None


def _text(node, path):
    if node is None:
        return None
    found = node.find(path)
    if found is None or found.text is None or not found.text.strip():
        return None
    return found.text.strip()


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_tag(root, suffix):
    """text of the first element whose tag ends with suffix (any depth)"""
    for node in root.iter():
        if isinstance(node.tag, str) and node.tag.upper().endswith(suffix) and node.text and node.text.strip():
            return node.text.strip()
    return None


def _stem(name):
    return posixpath.splitext(posixpath.basename(name))[0]


def parse_name(name):
    """native product name -> (platform index, native mode, native level),
    or None when the name is not a GEOSAT one."""
    name = _stem(name)
    match = GEOSAT1_NAME.match(name)
    if match:
        return '1', match.group(1).upper(), match.group(2).upper()
    match = GEOSAT2_NAME.match(name)
    if match:
        return '2', match.group(1).upper(), match.group(2).upper()
    return None


class Product_Geosat(Product_Directory):

    #
    METADATA_SUFFIX = '.DIM'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        # one DIMAP document per product or per component
        self.metContentName = []
        self.metContent = []
        self.imageNames = []
        self.quicklookNames = []
        self.components = []
        if self.debug != 0:
            print(" init class Product_Geosat")

    #
    # read matadata file
    #
    def getMetadataInfo(self, index=0):
        pass

    #
    # extract the GEOSAT interresting piece in working folder:
    # - DIMAP metadata (.dim)
    # - quicklook images
    # the GeoTIFF images stay in the ZIP (they go as-is into measurements/)
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        if self.debug != 0:
            print(" will extract directory product '%s' to path: %s" % (self.path, folder))

        self.EXTRACTED_PATH = folder
        self.contentList = []
        with zipfile.ZipFile(self.path) as z:
            for n, name in enumerate(z.namelist()):
                if self.debug != 0:
                    print("  extract[%d]:%s" % (n, name))
                if name.endswith('/'):
                    continue
                base = posixpath.basename(name).upper()
                keep = False
                if base.endswith(self.METADATA_SUFFIX):  # metadata
                    self.metContentName.append(name)
                    self.metContent.append(z.read(name))
                    keep = True
                elif base.endswith(IMAGE_EXT):  # image
                    self.imageNames.append(name)
                elif base.endswith(QUICKLOOK_EXT):  # quicklook
                    self.quicklookNames.append(name)
                    keep = True
                if keep and dont_extract != True:
                    dest = os.path.join(folder, name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as outfile:
                        outfile.write(z.read(name))
                self.contentList.append(name)

        if not self.metContent:
            raise Exception("is not a GEOSAT product: no DIMAP .dim document")
        if not self.imageNames:
            raise Exception("is not a GEOSAT product: no GeoTIFF image")

    #
    #
    #
    def extractMetadata(self, met=None):
        if met is None:
            raise Exception("metadata is None")
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")
        self.metadata = met

        documents = [self.parseDocument(name, data)
                     for name, data in zip(self.metContentName, self.metContent)]
        self.components = self.buildComponents(documents)
        first = self.components[0]

        # spec Table 14: orbitDirection mandatory for GEOSAT-2 only
        if first['platform'] == '2':
            missing = [c['document'] for c in self.components if c['orbitDirection'] is None]
            if missing:
                raise Exception("no orbit direction (%s) in %s"
                                % (" / ".join(ORBIT_DIRECTION_CODES), ", ".join(sorted(set(missing)))))

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)
        met.addLocalAttribute("originalName", self.origName)

        # sensing times: the outer bounds of the components
        start = min(c['begin'] for c in self.components)
        stop = max(c['end'] for c in self.components)
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date (spec Table 19), and package creation date
        # (spec Table 7): now
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, first['productionDate'])
        created = normalise_utc(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f'))
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # platform: <MMM> of the package name is the 'DE' of METADATA_PLATFORM
        # (cfg) + the satellite index: DE1 / DE2 (spec Table 1)
        platform = first['platform']
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform)
        met.addLocalAttribute("platformShortName", PLATFORMS[platform][0])
        met.addLocalAttribute("instrumentShortName", PLATFORMS[platform][1])
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, PLATFORMS[platform][1])

        self.buildTypeCode()

        # spec Table 18: mandatory for a geo-referenced product
        if first['crs'] is not None:
            met.addLocalAttribute("referenceSystemIdentifier", first['crs'])
        elif first['level'] in ORTHO_LEVELS:
            raise Exception("orthorectified product without a CRS: %s" % first['document'])

        # spec Table 21: optional, left out when the product has none
        if first['cloudCover'] is not None:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, first['cloudCover'])

        met.addLocalAttribute("components", [{
            "operationalMode": c['operationalMode'],
            "kind": c['kind'],
            "begin": c['begin'],
            "end": c['end'],
            "resolution": c['resolution'],
            "angles": c['angles'],
            "orbitNumber": c['orbitNumber'],
            "orbitDirection": c['orbitDirection'],
            "previewSuffix": c['previewSuffix'],
        } for c in self.components])
        met.addLocalAttribute("measurements", [c['measurement'] for c in self.components])

        # footprint: the first component's (the MS one in a bundle)
        met.addLocalAttribute("footprintRing", first['ring'])
        met.setMetadataPair(metadata.METADATA_FOOTPRINT,
                            " ".join("%s %s" % (lat, lon) for lon, lat in first['ring']))

    #
    # one DIMAP document -> its metadata, shared by the component(s) it describes
    #
    def parseDocument(self, name, data):
        root = ET.fromstring(data)
        dim_dir = posixpath.dirname(name)
        source = root.find('Dataset_Sources/Source_Information')
        scene = source.find('Scene_Source') if source is not None else None
        if scene is None:
            raise Exception("no Dataset_Sources/Source_Information/Scene_Source in %s" % name)

        # platform, mode and level: from the dataset name, else the document
        # file name, else the delivery name
        dataset_name = _text(root, 'Dataset_Id/DATASET_NAME')
        parsed = None
        for candidate in (dataset_name, name, self.origName):
            parsed = parse_name(candidate or '')
            if parsed:
                break
        if parsed is None:
            raise Exception("can not read the GEOSAT mode / level from %s (DATASET_NAME '%s')"
                            % (name, dataset_name))
        platform, mode, level = parsed
        product_type_level = (_text(root, 'Production/PRODUCT_TYPE') or '')[-2:].upper()
        if product_type_level and product_type_level != level:
            raise Exception("level %s of the name and PRODUCT_TYPE %s disagree in %s"
                            % (level, _text(root, 'Production/PRODUCT_TYPE'), name))
        mission_index = _text(scene, 'MISSION_INDEX')
        if mission_index is not None and not mission_index_agrees(mission_index, _text(scene, 'MISSION'), platform):
            raise Exception("MISSION_INDEX %s and name platform DE%s disagree in %s"
                            % (mission_index, platform, name))

        begin, end = self.timesOf(scene, name)

        # angles (spec Table 13): each is written only when present
        angles = {}
        for key, tag in (('illuminationAzimuthAngle', 'SUN_AZIMUTH'),
                         ('illuminationElevationAngle', 'SUN_ELEVATION'),
                         ('incidenceAngle', 'INCIDENCE_ANGLE')):
            value = _float(_text(scene, tag))
            if value is not None:
                angles[key] = value

        # resolution (spec Table 11, mandatory): the native pixel size,
        # else the nominal one of the product type (Tables 2 / 3)
        resolution = _float(_text(scene, 'PIXEL_RESOLUTION_X')) or _float(_text(scene, 'THEORETICAL_RESOLUTION'))

        production = production_utc(_text(root, 'Production/DATASET_PRODUCTION_DATE'))
        if production is None:
            raise Exception("no Production/DATASET_PRODUCTION_DATE in %s" % name)

        quality = self.qualityOf(root)
        direction = None
        for code in ORBIT_DIRECTION_CODES:
            if quality.get(code):
                direction = DIRECTIONS.get(quality[code].strip().upper())
                if direction is None:
                    raise Exception("invalid orbit direction %s='%s' in %s" % (code, quality[code], name))
                break
        cloud = None
        for code in CLOUD_COVER_CODES:
            cloud = _float(quality.get(code))
            if cloud is not None:
                break
        if cloud is not None and cloud < 0:  # -1: not computed
            cloud = None

        # CRS: the EPSG code, else the authority of the WKT
        crs = crs_uri(_find_tag(root, 'HORIZONTAL_CS_CODE'))
        if crs is None:
            crs = crs_uri(wkt_epsg(_find_tag(root, 'PROJECTION_OGCWKT')))

        images = [posixpath.normpath(posixpath.join(dim_dir, f.get('href')))
                  for f in root.iter('DATA_FILE_PATH') if f.get('href')]
        if not images:  # no Data_Access: the images next to the document
            images = [i for i in self.imageNames if posixpath.dirname(i) == dim_dir]
        missing = [i for i in images if i not in self.contentList]
        if not images or missing:
            raise Exception("image file(s) of %s not in the delivery: %s" % (name, missing or 'none found'))

        ql = root.find('Dataset_Id/DATASET_QL_PATH')
        ql = posixpath.normpath(posixpath.join(dim_dir, ql.get('href'))) if ql is not None and ql.get('href') else None

        return {
            'document': name,
            'dimDir': dim_dir,
            'datasetName': dataset_name or _stem(name),
            'platform': platform,
            'mode': mode,
            'level': level,
            'begin': begin,
            'end': end,
            'angles': angles,
            'resolution': resolution,
            'cloudCover': cloud,
            'productionDate': production,
            'orbitNumber': self.orbitNumberOf(root, quality, [dataset_name, name, self.origName]),
            'orbitDirection': direction,
            'crs': crs,
            'ring': self.footprintOf(root, name),
            'images': images,
            'quicklook': ql if ql in self.quicklookNames else None,
        }

    #
    # sensing times (spec Table 12): START_TIME / STOP_TIME, else the
    # imaging instant; a missing end is the beginning
    #
    def timesOf(self, scene, name):
        imaging_date = _text(scene, 'IMAGING_DATE')

        def datetime_of(value):
            if value is None:
                return None
            if 'T' not in value and ' ' not in value.strip():  # a time of day only
                if imaging_date is None:
                    raise Exception("time '%s' without IMAGING_DATE in %s" % (value, name))
                value = "%sT%s" % (imaging_date, value)
            return normalise_utc(value)

        begin = datetime_of(_text(scene, 'START_TIME'))
        end = datetime_of(_text(scene, 'STOP_TIME'))
        if begin is None:
            begin = datetime_of(_text(scene, 'IMAGING_TIME'))
        if begin is None:
            raise Exception("no acquisition time in %s" % name)
        return begin, end or begin

    #
    # Quality_Assessment parameters, by code
    #
    def qualityOf(self, root):
        quality = {}
        for param in root.iter('Quality_Parameter'):
            code = _text(param, 'QUALITY_PARAMETER_CODE')
            if code is not None:
                quality[code.upper()] = _text(param, 'QUALITY_PARAMETER_VALUE')
        return quality

    #
    # orbit number (spec Table 14, mandatory): a *ORBIT_NUMBER element or an
    # *:ORB* quality parameter of the document, else the ..._DE2_<orbit>_<id>
    # part of the name. A product that carries none falls back to the cfg
    # value (METADATA_ORBIT), with a warning.
    #
    def orbitNumberOf(self, root, quality, names):
        number = _find_tag(root, 'ORBIT_NUMBER')
        if number is None:
            number = next((v for k, v in quality.items()
                           if re.search(r':(ORB|ORBIT|ORBIT_NUMBER|ABS_ORBIT)$', k) and v), None)
        if number is None:
            for candidate in names:
                match = NAME_ORBIT.search(_stem(candidate or ''))
                if match:
                    number = match.group(1)
                    break
        if number is not None:
            try:
                return int(float(number))
            except ValueError:
                raise Exception("invalid orbit number '%s'" % number)

        number = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        if not self.metadata.valueExists(number):
            raise Exception("no orbit number in the product, and none in the cfg")
        print(" WARNING: no orbit number in the product: cfg value used (%s)" % number)
        return int(number)

    #
    # footprint: the Source_Frame vertices (else the Dataset_Frame ones), as
    # a closed GeoJSON ring [[lon, lat], ...], counterclockwise
    # (RFC 7946 section 3.1.6)
    #
    def footprintOf(self, root, name):
        vertices = root.findall('Dataset_Sources/Source_Information/Source_Frame/Vertex')
        if not vertices:
            vertices = root.findall('Dataset_Frame/Vertex')
        ring = []
        for vertex in vertices:
            lon = _float(_text(vertex, 'FRAME_LON'))
            lat = _float(_text(vertex, 'FRAME_LAT'))
            if lon is None or lat is None:
                raise Exception("invalid footprint vertex in %s" % name)
            ring.append([lon, lat])
        if len(ring) < 3:
            raise Exception("can not find footprint vertex in %s" % name)
        if ring[0] != ring[-1]:
            ring.append(list(ring[0]))
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
        if area < 0:
            ring.reverse()
        return ring

    #
    # documents -> components:
    # - one document, one image (or one tiled image set): one component
    # - one PM4 / STP document with several images: one component per image,
    #   its kind from the image name (DE2_PAN_... / DE2_MS4_...)
    # - several documents: one component each (PAN + MS4: bundle; two views
    #   of the same kind: stereo pair)
    #
    def buildComponents(self, documents):
        platforms = {d['platform'] for d in documents}
        levels = {d['level'] for d in documents}
        if len(platforms) != 1 or len(levels) != 1:
            raise Exception("DIMAP documents of different platforms / levels in one delivery")

        if len(documents) == 1 and documents[0]['mode'] in (BUNDLE_MODE, STEREO_MODE):
            doc = documents[0]
            if len(doc['images']) < 2:
                raise Exception("%s product %s with a single image" % (doc['mode'], doc['document']))
            components = [self.component(doc, self.fileKind(image, doc), [image], split=True)
                          for image in doc['images']]
            mode = doc['mode']
        else:
            components = [self.component(d, self.kindOf(d['mode'], d['document']), d['images'])
                          for d in documents]
            mode = documents[0]['mode'] if len(documents) == 1 else None

        if len(components) == 1:
            if mode in (BUNDLE_MODE, STEREO_MODE):
                raise Exception("%s product with a single component" % mode)
            components[0]['productKind'] = components[0]['kind']
            return components

        kinds = [c['kind'] for c in components]
        if sorted(kinds) == sorted(BUNDLE_ORDER) and mode in (None, BUNDLE_MODE):
            components.sort(key=lambda c: BUNDLE_ORDER.index(c['kind']))
            for c in components:
                c['productKind'] = 'BDL'
                c['operationalMode'] = BUNDLE_OPERATIONAL_MODE
                c['previewSuffix'] = BUNDLE_PREVIEW_SUFFIX[c['kind']]
                if c['split']:
                    c['resolution'] = NOMINAL_RESOLUTION[(c['kind'], c['level'])]
            return components
        if len(components) == 2 and len(set(kinds)) == 1 and kinds[0] in STEREO_TYPES \
                and mode in (None, STEREO_MODE):
            for n, c in enumerate(components):
                c['productKind'] = 'STEREO'
                c['operationalMode'] = STEREO_OPERATIONAL_MODE[c['kind']]
                c['previewSuffix'] = '_%d' % (n + 1)
                if c['split']:
                    c['resolution'] = STEREO_RESOLUTION
            return components
        raise Exception("unsupported GEOSAT component set: %s (only PAN + MS4 bundles"
                        " and PAN / PSH stereo pairs)" % ", ".join(kinds))

    def kindOf(self, mode, where):
        kind = KINDS.get(mode)
        if kind is None:
            raise Exception("unsupported GEOSAT mode '%s' in %s" % (mode, where))
        return kind

    def fileKind(self, image, doc):
        match = GEOSAT2_FILE_MODE.match(posixpath.basename(image))
        if not match:
            raise Exception("can not read the spectral mode of image %s in %s product %s"
                            % (image, doc['mode'], doc['document']))
        return self.kindOf(match.group(1).upper(), image)

    def component(self, doc, kind, images, split=False):
        resolution = doc['resolution']
        if resolution is None:
            resolution = NOMINAL_RESOLUTION.get((kind, doc['level']))
            if resolution is None:
                raise Exception("no resolution in %s" % doc['document'])
        return dict(doc,
                    kind=kind,
                    split=split,
                    resolution=resolution,
                    operationalMode=OPERATIONAL_MODE[kind],
                    previewSuffix='',
                    measurement=self.measurementOf(doc, images),
                    preview=self.previewOf(doc, images, split))

    #
    # measurements link (spec Table 23): the component image inside the
    # unpacked delivery; several images (tiles) have no single file, their
    # DIMAP document (which lists them) is linked instead
    #
    def measurementOf(self, doc, images):
        if len(images) > 1:
            return {"href": doc['document'], "type": "application/xml"}
        # a DIMAP GeoTIFF is not the cloud-optimized profile of the spec
        # example: plain image/tiff
        return {"href": images[0], "type": "image/tiff"}

    #
    # the component quicklook: the document's DATASET_QL_PATH, else the one
    # named after the image (<image>_QL.png, <image stem>_QL.png,
    # <image stem>.png ...), else the only quicklook next to the document;
    # None: the overview is made from the image itself
    #
    def previewOf(self, doc, images, split):
        if doc['quicklook'] and not split:
            return doc['quicklook']
        for image in images:
            stem = posixpath.splitext(image)[0].upper()
            for ql in self.quicklookNames:
                if posixpath.splitext(ql)[0].upper() in (stem, stem + '_QL', image.upper() + '_QL'):
                    return ql
        if not split:
            candidates = [q for q in self.quicklookNames if posixpath.dirname(q) == doc['dimDir']]
            if len(candidates) == 1:
                return candidates[0]
        return None

    #
    # spec Tables 2 / 3:
    # GEOSAT-1  L1_GEO_MS_ / L1_ORT_MS_ / L2_ORT_MS_   (native 1R / 1T / 2T)
    # GEOSAT-2  L1BORTRPAN / L1CORT_PAN                 (PAN)
    #           L1BORTRMS_ / L1CORT_MS_                 (MS4)
    #           L1BORTRPSH / L1CORT_PSH / L1DORTEPSH    (PSH, PS4)
    #           L1BORTRBDL / L1CORT_BDL / L1DORTEBDL    (bundle PAN + MS4)
    #           SYNSTERPAN / SYNSTERPSH                 (stereo pair)
    #
    def buildTypeCode(self):
        first = self.components[0]
        platform, level, kind = first['platform'], first['level'], first['productKind']
        if kind == 'STEREO':
            typecode = STEREO_TYPES[first['kind']]
            processing_level, level_code = STEREO_LEVEL, LEVELS[level][1]
        else:
            typecode = PRODUCT_TYPES.get((platform, kind, level))
            processing_level, level_code = LEVELS[level]
        if typecode is None:
            raise Exception("buildTypeCode; no product type in the specialization for GEOSAT-%s %s level %s"
                            % (platform, kind, level))

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, processing_level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE,
                                      ",".join(c['operationalMode'] for c in self.components))
        print("TYPECODE SET TO: %s (level %s)" % (typecode, processing_level))

    #
    # write one overview PNG per component next to the manifest, named
    # <EO name><suffix>.PNG as the manifest previews hrefs (section 4): from
    # the component quicklook, else from its image
    #
    def writeQuicklooks(self, out_dir, eo_product_name):
        from PIL import Image
        written = []
        for c in self.components:
            if c['preview'] is not None:
                src = os.path.join(self.EXTRACTED_PATH, c['preview'])
            else:
                src = self.extractImage(c)
            dest = os.path.join(out_dir, "%s%s.PNG" % (eo_product_name, c['previewSuffix']))
            try:
                with Image.open(src) as im:
                    im.thumbnail((OVERVIEW_MAX_SIZE, OVERVIEW_MAX_SIZE))
                    if im.mode not in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA', 'I', 'I;16'):
                        im = im.convert('RGB')
                    im.save(dest, format="PNG")
            except Exception as e:
                raise Exception("can not make the overview of %s from %s: %s"
                                % (c['document'], os.path.basename(src), e))
            written.append(dest)
        return written

    def extractImage(self, c):
        href = c['measurement']['href']
        if not href.upper().endswith(IMAGE_EXT):
            raise Exception("no quicklook for %s and no single image to make one" % c['document'])
        dest = os.path.join(self.EXTRACTED_PATH, href)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zipfile.ZipFile(self.path) as z, open(dest, 'wb') as outfile:
                outfile.write(z.read(href))
        return dest

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
