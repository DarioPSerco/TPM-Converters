"""This class represents a RapidEye native product.

The entry file is the product metadata `<product stem>_metadata.xml`
(`re:EarthObservation`). The native product unit is every file under the entry
folder whose name starts with the stem - the same rule the packager uses to
fill measurements/. A delivery folder may hold several products.

Supported product types (EOPF-EOS specialization for RapidEye, Tables 1 and 2),
keyed by the native level of the XML (`eop:productType`):

L1BOPT_MS_: L1B, one image per band, <stem>_band<n>.ntf                   (5 bands)
L3_ORT_MS_: L3A, one multiband image, <stem>.tif                 (3 or 5 bands)

The native format is not described by the specialization and no real product
has been converted yet: see test/fixtures/SYNTHETIC_FIXTURE_NOTE.md.
"""
import os
import re
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from lxml import etree

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

METADATA_SUFFIX = "_metadata.xml"

# custom metadata keys (mission-local, like COSMO-SkyMed's)
PRODUCT_STEM = 'product_stem'
PLATFORM_SHORT_NAME = 'platform_short_name'
NUM_BANDS = 'num_bands'
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

OPERATIONAL_MODE = 'MS'

# native level -> (product type, processingLevel (Table 17),
# processedLevel code (Table 18), allowed band counts (Table 2))
NATIVE_LEVELS = {
    'L1B': ('L1BOPT_MS_', '1B', 'L1B', (5,)),
    'L3A': ('L3_ORT_MS_', '3', 'L3', (3, 5)),
    'L3': ('L3_ORT_MS_', '3', 'L3', (3, 5)),
}

SINGLE_IMAGE_RE = re.compile(r"^\.(tif|tiff)$", re.IGNORECASE)
BAND_IMAGE_RE = re.compile(r"^_band(\d)\.(ntf|nitf|tif|tiff)$", re.IGNORECASE)
BROWSE_RE = re.compile(r"^_browse\.(tif|tiff)$", re.IGNORECASE)
PLATFORM_RE = re.compile(r"^(?:RE|RAPIDEYE)[-_ ]?0*([1-5])$", re.IGNORECASE)
FILE_PLATFORM_RE = re.compile(r"_RE([1-5])_", re.IGNORECASE)
FILE_LEVEL_RE = re.compile(r"_(1B|3A)(?:[-_]|$)", re.IGNORECASE)

# spec Table 15, in metres, grouped by spectralRange:
# blue, green, red / red edge / near infrared
WAVELENGTHS = {
    3: [('VIS', [(440e-9, 510e-9), (520e-9, 590e-9), (630e-9, 685e-9)])],
    5: [('VIS', [(440e-9, 510e-9), (520e-9, 590e-9), (630e-9, 685e-9)]),
        ('VNIR', [(690e-9, 730e-9)]),
        ('NIR', [(760e-9, 850e-9)])],
}

# zero-based (red, green, blue) band indices per band count, for the overview:
# 3 bands R,G,B; 5 bands B,G,R,RE,NIR
RGB_BANDS = {3: (0, 1, 2), 5: (2, 1, 0)}

OVERVIEW_MAX_SIZE = 1000

# NITF has no media type in the EOPF-EOS schema link-types thesaurus
MEDIA_TYPES = {".tif": "image/tiff", ".tiff": "image/tiff",
               ".ntf": "application/octet-stream", ".nitf": "application/octet-stream"}


def normalise_utc(value):
    """RapidEye datetime ('...Z' or '+00:00', with or without fraction) ->
    RFC 3339 UTC with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:?\d{2})?$", text)
    if not match:
        raise Exception("unexpected RapidEye datetime format: '%s'" % value)
    base, frac, offset = match.groups()
    frac = (frac or "")[:6].ljust(6, "0")
    parsed = datetime.fromisoformat("%s.%s%s" % (base.replace(' ', 'T'), frac, offset or '+00:00'))
    parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (parsed.microsecond // 1000)


def product_stem_of(entry_name):
    """'<product stem>_metadata.xml' -> '<product stem>'."""
    name = os.path.basename(str(entry_name))
    if not name.lower().endswith(METADATA_SUFFIX):
        raise Exception("not a RapidEye product metadata file (<product stem>%s): %s"
                        % (METADATA_SUFFIX, entry_name))
    return name[:-len(METADATA_SUFFIX)]


def product_files(folder, stem):
    """Every file under folder belonging to the product: its name is the stem
    followed by '_' or '.'. Sorted by relative path."""
    found = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for name in sorted(files):
            if name.startswith(stem + "_") or name.startswith(stem + "."):
                found.append(os.path.join(root, name))
    return sorted(found, key=lambda p: os.path.relpath(p, folder).replace(os.sep, "/"))


def media_type_of(filename):
    ext = os.path.splitext(str(filename).lower())[1]
    if ext not in MEDIA_TYPES:
        raise Exception("no media type known for: %s" % filename)
    return MEDIA_TYPES[ext]


def platform_short_name(serial):
    """'RE-3', 'RE3', 'RapidEye-3' -> 'RapidEye-3' (spec Table 8), or None."""
    match = PLATFORM_RE.match(str(serial or '').strip())
    return "RapidEye-%s" % match.group(1) if match else None


def tiff_band_count(path):
    """Samples per pixel of a GeoTIFF: the shortest axis of the image."""
    import tifffile
    with tifffile.TiffFile(path) as tif:
        sizes = dict(zip(tif.series[0].axes, tif.series[0].shape))
    for axis in ('S', 'C', 'I'):
        if axis in sizes:
            return int(sizes[axis])
    return 1


def parse_ring(ring_node):
    """Points of a gml LinearRing as [[lon, lat], ...]: gml:coordinates are
    'lon,lat lon,lat ...' (GML 2 order), gml:posList 'lat lon lat lon ...'
    (GML 3 order for EPSG:4326)."""
    points = []
    coordinates = ring_node.xpath("./*[local-name()='coordinates']")
    pos_list = ring_node.xpath("./*[local-name()='posList']")
    if coordinates:
        for token in (coordinates[0].text or "").split():
            parts = token.split(',')
            if len(parts) < 2:
                raise Exception("invalid gml:coordinates token: '%s'" % token)
            points.append([float(parts[0]), float(parts[1])])
    elif pos_list:
        values = [float(v) for v in (pos_list[0].text or "").split()]
        if len(values) % 2:
            raise Exception("odd number of values in gml:posList")
        points = [[values[i + 1], values[i]] for i in range(0, len(values), 2)]
    for lon, lat in points:
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise Exception("footprint point out of range: lon=%s lat=%s" % (lon, lat))
    return points


class Product_Rapideye(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        self.stem = product_stem_of(self.path)
        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.preview_path = None
        self.tmpSize = 0

        self.xml = etree.parse(self.path)
        root = etree.QName(self.xml.getroot()).localname
        if root != 'EarthObservation':
            raise Exception("not a RapidEye metadata XML (root '%s'): %s" % (root, path))

        self.files = product_files(self.EO_FOLDER, self.stem)
        self.image_file = None      # main image, absolute path
        self.band_files = []        # L1B: one image per band, absolute paths
        self.browse_file = None     # native browse if delivered, absolute path
        self.typecode = None
        self.processing_level = None
        self.level_code = None
        self.allowed_bands = None
        self.num_bands = None
        self._select_assets()

        if self.debug != 0:
            print(" init class Product_Rapideye (%s)" % self.stem)

    # -- assets -----------------------------------------------------------

    def _select_assets(self):
        for path in self.files:
            rest = os.path.basename(path)[len(self.stem):]
            if SINGLE_IMAGE_RE.match(rest) and self.image_file is None:
                self.image_file = path
            elif BAND_IMAGE_RE.match(rest):
                self.band_files.append(path)
            elif BROWSE_RE.match(rest) and self.browse_file is None:
                self.browse_file = path
        if self.image_file is None and self.band_files:
            self.image_file = self.band_files[0]
        if self.image_file is None:
            raise Exception("no RapidEye image (%s.tif or %s_band<n>.ntf) in %s; files: %s"
                            % (self.stem, self.stem, self.EO_FOLDER,
                               ", ".join(os.path.basename(f) for f in self.files) or "none"))

    # -- XML access -------------------------------------------------------

    def xml_text(self, *local_names):
        """Text of the first element reached by the local-name path
        (namespace agnostic), or None."""
        xpath = "//*[local-name()='%s']" % local_names[0]
        for name in local_names[1:]:
            xpath += "/*[local-name()='%s']" % name
        nodes = self.xml.xpath(xpath)
        if not nodes:
            return None
        text = (nodes[0].text or "").strip()
        return text or None

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
        """No extraction to disk is needed. Sum the size of the product files,
        which is what lands in measurements/."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        self.EXTRACTED_PATH = folder
        self.contentList = list(self.files)
        self.tmpSize = sum(os.stat(f).st_size for f in self.files)
        if self.debug != 0:
            for n, f in enumerate(self.files):
                print(" ## product content[%d]:'%s'" % (n, os.path.relpath(f, self.EO_FOLDER)))
        print((" #### native product %s: %d file(s), %d bytes"
               % (self.stem, len(self.files), self.tmpSize)))

    def measurement_href(self):
        """Path of the main image inside measurements/, as packaged."""
        return os.path.relpath(self.image_file, self.EO_FOLDER).replace(os.sep, "/")

    def writeQuicklook(self, destPath):
        """Write the overview PNG at destPath, from the native browse when the
        product carries one (used as delivered), else from the multiband
        GeoTIFF: red/green/blue bands, 2-98 percentile stretch per band over
        the valid (non-zero) pixels. No-data pixels become transparent. NITF
        band images cannot be rendered: an L1B product needs its browse."""
        import tifffile
        from PIL import Image

        source = self.browse_file or self.image_file
        if os.path.splitext(source)[1].lower() not in ('.tif', '.tiff'):
            raise Exception("no overview source for %s: no %s_browse.tif and %s is not a GeoTIFF"
                            % (self.stem, self.stem, os.path.basename(source)))
        is_browse = source == self.browse_file

        def spatial_size(level):
            sizes = dict(zip(level.axes, level.shape))
            return max(sizes.get('Y', 0), sizes.get('X', 0))

        with tifffile.TiffFile(source) as tif:
            series = tif.series[0]
            level = series
            for candidate in series.levels[1:]:
                if spatial_size(candidate) < OVERVIEW_MAX_SIZE:
                    break
                level = candidate
            data = level.asarray()
            axes = level.axes

        # -> (rows, cols, bands); 'S' (samples) or 'C'/'I' (planes) is the band axis
        if data.ndim == 2:
            data = data[:, :, np.newaxis]
        elif axes.index('Y') > 0:
            data = np.moveaxis(data, 0, -1)
        bands = data.shape[-1]

        if is_browse and data.dtype == np.uint8 and bands >= 3:
            rgb = data[:, :, :3]
            if bands >= 4:
                alpha = data[:, :, 3]
            else:
                alpha = np.where(np.any(rgb > 0, axis=-1), 255, 0).astype(np.uint8)
        else:
            if bands < 3:
                raise Exception("cannot build an RGB overview from %d band(s): %s" % (bands, source))
            red, green, blue = RGB_BANDS.get(bands, (0, 1, 2))
            picked = data[:, :, [red, green, blue]].astype('float64')
            valid = np.any(picked > 0, axis=-1)
            rgb = np.zeros(picked.shape, dtype=np.uint8)
            for i in range(3):
                band = picked[:, :, i]
                values = band[valid]
                if values.size == 0:
                    continue
                low, high = np.percentile(values, (2.0, 98.0))
                if high <= low:
                    high = low + 1.0
                rgb[:, :, i] = (np.clip((band - low) / (high - low), 0, 1) * 255).astype(np.uint8)
            alpha = np.where(valid, 255, 0).astype(np.uint8)

        image = Image.fromarray(np.dstack([rgb, alpha]))  # (rows, cols, 4) uint8 -> RGBA
        image.thumbnail((OVERVIEW_MAX_SIZE, OVERVIEW_MAX_SIZE), Image.Resampling.LANCZOS)
        image.save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### overview written: %s (from %s)" % (destPath, os.path.basename(source))))
        return destPath

    # -- metadata ---------------------------------------------------------

    def _native_level(self):
        """Native level from the XML, else from the '_3A' / '_1B' file name
        token."""
        level = self.xml_text('EarthObservationMetaData', 'productType')
        if level is None:
            match = FILE_LEVEL_RE.search(self.stem)
            level = "L%s" % match.group(1) if match else None
        if level is None:
            raise Exception("no native level (eop:productType) in %s" % self.path)
        level = level.upper()
        if level not in NATIVE_LEVELS:
            raise Exception("unsupported RapidEye native level: '%s' in %s" % (level, self.path))
        return level

    def _band_count(self):
        """Band count from the XML, else from the delivered images."""
        count = self.xml_text('numBands')
        if count is not None:
            return int(count)
        if self.band_files:
            return len(self.band_files)
        return tiff_band_count(self.image_file)

    def buildTypeCode(self, processInfo):
        level = self._native_level()
        self.typecode, self.processing_level, self.level_code, self.allowed_bands = NATIVE_LEVELS[level]
        self.num_bands = self._band_count()
        if self.num_bands not in self.allowed_bands:
            raise Exception("band count %s not allowed for product type %s"
                            % (self.num_bands, self.typecode))

        self.metadata.setMetadataPair(NUM_BANDS, self.num_bands)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, OPERATIONAL_MODE)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, self.processing_level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, self.level_code)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)
        print(("TYPECODE SET TO: %s (%d bands, level %s)" % (self.typecode, self.num_bands, level)))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")

        self.metadata = met
        met.setMetadataPair(PRODUCT_STEM, self.stem)

        # sensing times; a missing end is set to the beginning (spec Table 11)
        start = normalise_utc(self.xml_text('validTime', 'TimePeriod', 'beginPosition')
                              or self.xml_text('Acquisition', 'acquisitionDateTime'))
        if start is None:
            raise Exception("no acquisition time in %s" % self.path)
        stop = normalise_utc(self.xml_text('validTime', 'TimePeriod', 'endPosition')) or start
        if stop < start:
            stop = start
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date (Table 17), else when the product was archived
        processed = normalise_utc(self.xml_text('processingDate') or self.xml_text('archivingDate'))
        if processed is None:
            raise Exception("no processingDate / archivingDate in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, processed)

        # package creation date (spec Table 6): now, the conversion time
        created = normalise_utc(datetime.now(timezone.utc).isoformat())
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # satellite -> platform (Table 8), from the XML, else the file name
        serial = self.xml_text('Platform', 'serialIdentifier')
        platform = platform_short_name(serial)
        if platform is None:
            match = FILE_PLATFORM_RE.search(os.path.basename(self.path))
            platform = "RapidEye-%s" % match.group(1) if match else None
        if platform is None:
            raise Exception("unknown RapidEye satellite: '%s' in %s" % (serial, self.path))
        met.setMetadataPair(PLATFORM_SHORT_NAME, platform)
        met.setMetadataPair(metadata.METADATA_SATELLITE, platform)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, 'REIS')

        # orbit direction
        orbit_direction = (self.xml_text('Acquisition', 'orbitDirection') or '').upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid or missing orbit direction: '%s' in %s"
                            % (orbit_direction, self.path))
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        self.buildTypeCode(processInfo)

        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the native product size; the base pipeline would
        # fill the eoSIP size here, so mark it as the other converters do
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # resolution: the delivered pixel size, else the sensor resolution
        resolution = self.xml_text('rowGsd') or self.xml_text('columnGsd') \
            or self.xml_text('Sensor', 'resolution')
        if resolution is None or float(resolution) <= 0:
            raise Exception("invalid or missing resolution in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, float(resolution))

        # sun angles (Table 13, mandatory)
        sun_azimuth = self.xml_text('Acquisition', 'illuminationAzimuthAngle')
        sun_elevation = self.xml_text('Acquisition', 'illuminationElevationAngle')
        if sun_azimuth is None or sun_elevation is None:
            raise Exception("missing sun azimuth / elevation in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, float(sun_azimuth))
        met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, float(sun_elevation))

        # across-track angle (Table 13, optional): the spacecraft view angle,
        # as SkySat's view_angle; along-track has no native source
        view_angle = self.xml_text('Acquisition', 'spaceCraftViewAngle')
        if view_angle is not None:
            met.addLocalAttribute("acrossTrackIncidenceAngle", float(view_angle))

        # cloud cover, percent (Table 19, left out when unavailable); a value
        # outside 0-100 means the native product was not assessed
        cloud = self.xml_text('EarthObservationResult', 'cloudCoverPercentage')
        if cloud is not None and 0.0 <= float(cloud) <= 100.0:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, round(float(cloud), 2))

        # CRS of a geo-referenced product (Table 16: when not supplied the
        # product is in the raw satellite frame, as L1B is)
        epsg = self.xml_text('spatialReferenceSystem', 'epsgCode')
        if epsg is not None:
            met.addLocalAttribute("referenceSystemIdentifier",
                                  "http://www.opengis.net/def/crs/EPSG/0/%d" % int(epsg))

        met.addLocalAttribute("nativeDataFile", self.measurement_href())
        met.addLocalAttribute("measurementsMediaType", media_type_of(self.image_file))

        print(("## resolution=%s; sun az/el=%s/%s; view=%s; cloud=%s"
               % (resolution, sun_azimuth, sun_elevation, view_angle, cloud)))

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint from the XML target: the exterior ring, closed and
        counter-clockwise as RFC 7946 wants. Several rings are replaced by the
        bounding box of all of them, since the specialization allows a Polygon
        only."""
        rings = self.xml.xpath("//*[local-name()='Footprint']//*[local-name()='LinearRing']")
        parsed = [parse_ring(node) for node in rings]
        parsed = [ring for ring in parsed if ring]
        if not parsed:
            raise Exception("no footprint LinearRing in %s" % self.path)
        if len(parsed) == 1:
            ring = parsed[0]
        else:
            points = [p for candidate in parsed for p in candidate]
            lons = [p[0] for p in points]
            lats = [p[1] for p in points]
            ring = [[min(lons), min(lats)], [max(lons), min(lats)],
                    [max(lons), max(lats)], [min(lons), max(lats)]]

        if ring[0] != ring[-1]:
            ring.append(list(ring[0]))
        if len(ring) < 4:
            raise Exception("degenerate footprint in %s" % self.path)
        # shoelace on lon/lat: positive area = counter-clockwise
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
        if area < 0:
            ring.reverse()

        self.metadata.addLocalAttribute("footprintRing", ring)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT,
                                      " ".join("%s %s" % (p[1], p[0]) for p in ring))

        flat = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
        flon = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))
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

    def toString(self):
        return "path:%s" % self.path

    def dump(self):
        print(self.toString())
