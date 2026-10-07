"""This class represents a PlanetScope native product (one Planet item).

The entry file is the item metadata `<item id>_metadata.json` (a GeoJSON
Feature: geometry + `properties`). The item assets sit next to it, either in
the same folder (Orders API delivery, possibly shared by several items) or in
per-asset sub-folders (legacy Data API download). The native product unit is
therefore every file under the entry folder whose name starts with the item
id - the same rule the packager uses to fill measurements/.

Metadata sources:
- `<item id>_metadata.json`: footprint, acquisition time, instrument,
  sun angles, view angle, cloud cover, pixel resolution, publication date;
- the asset XML `<item id>_<asset>_metadata.xml` (Planet `ps:EarthObservation`):
  validity period, orbit direction, incidence angle, processor name and
  version, native processing level (`productType`), band count, EPSG code.

Supported product types (EOPF-EOS specialization for PlanetScope, Table 2),
keyed by the main image asset of the item:

L3_AO__MS_: <id>_3B_AnalyticMS[_8b].tif, <id>_3B_Analytic.tif  (MS3B/MS4B/MS8B)
L3_SRO_MS_: <id>_3B_AnalyticMS_SR[_8b].tif                     (MS4B/MS8B)
L1AAB__MS_: <id>_1A_AnalyticMS[_8b].tif                        (MS4B/MS8B)
L1BAB__MS_: <id>_1B_AnalyticMS[_8b].tif                        (MS4B/MS8B)
L3_VO__MS_: <id>_3B_Visual.tif                                 (MS3B)
L3_OT__MS_: PSOrthoTile item, <id>_BGRN_Analytic.tif / <id>_BGRN_SR.tif (MS4B)

When an item carries several image assets, the first one in IMAGE_ASSETS
order is the main image (it fixes the product type, the measurements link and
the overview source); the other assets are still carried in measurements/.
"""
import json
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

METADATA_SUFFIX = "_metadata.json"
XML_SUFFIX = "_metadata.xml"

ITEM_TYPE_SCENE = ("PSScene", "PSScene3Band", "PSScene4Band")
ITEM_TYPE_ORTHO_TILE = "PSOrthoTile"

# custom metadata keys (mission-local, like COSMO-SkyMed's)
ITEM_ID = 'item_id'
ITEM_TYPE = 'item_type'
INSTRUMENT_ID = 'instrument_id'
NUM_BANDS = 'num_bands'
PROCESSED_LEVEL_CODE = 'processed_level_code'
PROCESSOR_NAME = 'processor_name'
PROCESSOR_VERSION = 'processor_version'
CREATION_TIME = 'creation_time'

# Main image assets, in order of preference (the legacy EO-SIP converter's
# order of importance): (regex on the file name after the item id,
# product type, native level, band count). The native level is checked
# against the asset XML productType.
IMAGE_ASSETS = (
    (r"_3B_AnalyticMS_8b\.tiff?$", 'L3_AO__MS_', 'L3B', 8),
    (r"_3B_AnalyticMS_SR_8b\.tiff?$", 'L3_SRO_MS_', 'L3B', 8),
    (r"_1B_AnalyticMS_8b\.tiff?$", 'L1BAB__MS_', 'L1B', 8),
    (r"_1A_AnalyticMS_8b\.tiff?$", 'L1AAB__MS_', 'L1A', 8),
    (r"_3B_AnalyticMS\.tiff?$", 'L3_AO__MS_', 'L3B', 4),
    (r"_3B_AnalyticMS_SR\.tiff?$", 'L3_SRO_MS_', 'L3B', 4),
    (r"_1B_AnalyticMS\.tiff?$", 'L1BAB__MS_', 'L1B', 4),
    (r"_1A_AnalyticMS\.tiff?$", 'L1AAB__MS_', 'L1A', 4),
    (r"_3B_Analytic\.tiff?$", 'L3_AO__MS_', 'L3B', 3),
    (r"_3B_Visual\.tiff?$", 'L3_VO__MS_', 'L3B', 3),
)
ORTHO_TILE_ASSETS = (
    (r"_BGRN_Analytic\.tiff?$", 'L3_OT__MS_', 'L3A', 4),
    (r"_BGRN_SR\.tiff?$", 'L3_OT__MS_', 'L3A', 4),
)

# visual assets are colour-balanced 8-bit RGB, used as-is for the overview
VISUAL_ASSET_RE = re.compile(r"(_3B_Visual|_RGB_Visual)\.tiff?$", re.IGNORECASE)

# band count -> operationalMode (spec Table 2)
OPERATIONAL_MODE = {3: 'MS3B', 4: 'MS4B', 8: 'MS8B'}

# spec Table 2: operational modes allowed per product type
ALLOWED_MODES = {
    'L3_AO__MS_': ('MS3B', 'MS4B', 'MS8B'),
    'L3_SRO_MS_': ('MS4B', 'MS8B'),
    'L1AAB__MS_': ('MS4B', 'MS8B'),
    'L1BAB__MS_': ('MS4B', 'MS8B'),
    'L3_OT__MS_': ('MS4B',),
    'L3_VO__MS_': ('MS3B',),
}

# native level -> processingLevel (spec Table 17)
PROCESSING_LEVEL = {'L1A': '1A', 'L1B': '1B', 'L3B': '3', 'L3A': '3'}

# instrument -> platformShortName (spec Tables 8 and 9)
PLATFORM_MAP = {'PS2': 'Dove', 'PS2.SD': 'Dove-R', 'PSB.SD': 'SuperDove'}

# zero-based (red, green, blue) band indices per band count, for the overview:
# 3 bands analytic R,G,B / visual R,G,B; 4 bands B,G,R,N; 8 bands
# coastal blue, blue, green I, green, yellow, red, red edge, NIR
RGB_BANDS = {3: (0, 1, 2), 4: (2, 1, 0), 8: (5, 3, 1)}

OVERVIEW_MAX_SIZE = 1000

MEDIA_TYPES = {".tif": "image/tiff", ".tiff": "image/tiff"}


def normalise_utc(value):
    """PlanetScope datetime (JSON '...Z' with microseconds, XML '+00:00' with
    or without fraction) -> RFC 3339 UTC with milliseconds
    (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:?\d{2})?$", text)
    if not match:
        raise Exception("unexpected PlanetScope datetime format: '%s'" % value)
    base, frac, offset = match.groups()
    # keep at most microseconds for fromisoformat, round down to milliseconds
    frac = (frac or "")[:6].ljust(6, "0")
    parsed = datetime.fromisoformat("%s.%s%s" % (base.replace(' ', 'T'), frac, offset or '+00:00'))
    parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (parsed.microsecond // 1000)


def item_id_of(entry_name):
    """'<item id>_metadata.json' -> '<item id>'."""
    name = os.path.basename(str(entry_name))
    if not name.lower().endswith(METADATA_SUFFIX):
        raise Exception("not a PlanetScope item metadata file (<item id>%s): %s"
                        % (METADATA_SUFFIX, entry_name))
    return name[:-len(METADATA_SUFFIX)]


def item_files(folder, item_id):
    """Every file under folder belonging to the item: its name is the item id
    followed by '_' or '.'. Sorted by relative path."""
    found = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for name in sorted(files):
            if name.startswith(item_id + "_") or name.startswith(item_id + "."):
                found.append(os.path.join(root, name))
    return sorted(found, key=lambda p: os.path.relpath(p, folder).replace(os.sep, "/"))


def media_type_of(filename):
    ext = os.path.splitext(str(filename).lower())[1]
    if ext not in MEDIA_TYPES:
        raise Exception("no media type known for: %s" % filename)
    return MEDIA_TYPES[ext]


# spec Table 14, in metres, per operationalMode, grouped by spectralRange:
# [(spectralRange, [(start, stop) per band, ...]), ...]
_VIS3 = [(465e-9, 515e-9), (547e-9, 583e-9), (650e-9, 680e-9)]
WAVELENGTHS = {
    'MS3B': [('VIS', _VIS3)],
    'MS4B': [('VIS', _VIS3), ('NIR', [(845e-9, 885e-9)])],
    'MS8B': [('VIS', [(431e-9, 452e-9), (465e-9, 515e-9), (513e-9, 549e-9),
                      (547e-9, 583e-9), (600e-9, 620e-9), (650e-9, 680e-9)]),
             ('VNIR', [(697e-9, 713e-9)]),
             ('NIR', [(845e-9, 885e-9)])],
}


class Product_Planetscope(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        self.item_id = item_id_of(self.path)
        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.preview_path = None
        self.tmpSize = 0

        with open(self.path, 'r', encoding='utf-8') as fd:
            self.item = json.load(fd)
        if not isinstance(self.item, dict) or 'properties' not in self.item:
            raise Exception("not a PlanetScope item metadata (no 'properties'): %s" % path)
        self.properties = self.item['properties']
        self.item_type = str(self.properties.get('item_type') or '')
        if self.item_type not in ITEM_TYPE_SCENE and self.item_type != ITEM_TYPE_ORTHO_TILE:
            raise Exception("unsupported PlanetScope item_type: '%s' in %s" % (self.item_type, path))

        self.files = item_files(self.EO_FOLDER, self.item_id)
        self.image_file = None      # main image, absolute path
        self.visual_file = None     # visual asset if delivered, absolute path
        self.xml_file = None
        self.xml = None
        self.typecode = None
        self.native_level = None
        self.num_bands = None
        self._select_assets()

        if self.debug != 0:
            print(" init class Product_Planetscope (%s, %s)" % (self.item_id, self.item_type))

    # -- assets -----------------------------------------------------------

    def _select_assets(self):
        table = ORTHO_TILE_ASSETS if self.item_type == ITEM_TYPE_ORTHO_TILE else IMAGE_ASSETS
        names = {f: os.path.basename(f)[len(self.item_id):] for f in self.files}

        for pattern, typecode, level, bands in table:
            regex = re.compile(pattern, re.IGNORECASE)
            hits = [f for f, rest in names.items() if regex.match(rest)]
            if hits:
                self.image_file = hits[0]
                self.typecode, self.native_level, self.num_bands = typecode, level, bands
                break
        if self.image_file is None:
            raise Exception("no supported PlanetScope image asset for item %s (%s) in %s; files: %s"
                            % (self.item_id, self.item_type, self.EO_FOLDER,
                               ", ".join(os.path.basename(f) for f in self.files) or "none"))

        for f in self.files:
            if VISUAL_ASSET_RE.search(os.path.basename(f)):
                self.visual_file = f
                break

        self.xml_file = self._select_xml()
        if self.xml_file is None:
            raise Exception("no asset metadata XML (<item id>_*%s) for item %s in %s"
                            % (XML_SUFFIX, self.item_id, self.EO_FOLDER))
        self.xml = etree.parse(self.xml_file)

    def _select_xml(self):
        """The asset XML describing the main image: '<image stem>_metadata.xml'
        first; for a surface reflectance image the analytic one it derives from
        ('_SR' dropped, as Planet ships it); else any analytic asset XML, else
        any asset XML of the item."""
        xmls = [f for f in self.files if f.lower().endswith(XML_SUFFIX)]
        by_name = {os.path.basename(f).lower(): f for f in xmls}
        stem = os.path.splitext(os.path.basename(self.image_file))[0]
        candidates = [stem + XML_SUFFIX, stem.replace("_SR", "") + XML_SUFFIX,
                      stem.replace("_SR", "_Analytic") + XML_SUFFIX]
        for candidate in candidates:
            if candidate.lower() in by_name:
                return by_name[candidate.lower()]
        for f in xmls:
            if "analytic" in os.path.basename(f).lower():
                return f
        return xmls[0] if xmls else None

    def xml_is_main_image_own(self):
        """True when the XML describes the main image itself (same stem), so
        its band count must match."""
        stem = os.path.splitext(os.path.basename(self.image_file))[0]
        return os.path.basename(self.xml_file).lower() == (stem + XML_SUFFIX).lower()

    # -- XML / JSON access ------------------------------------------------

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

    def prop(self, name, default=None):
        value = self.properties.get(name)
        return default if value is None else value

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
        """No extraction to disk is needed. Sum the size of the item files,
        which is what lands in measurements/."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        self.EXTRACTED_PATH = folder
        self.contentList = list(self.files)
        self.tmpSize = sum(os.stat(f).st_size for f in self.files)
        if self.debug != 0:
            for n, f in enumerate(self.files):
                print(" ## product content[%d]:'%s'" % (n, os.path.relpath(f, self.EO_FOLDER)))
        print((" #### native item %s: %d file(s), %d bytes"
               % (self.item_id, len(self.files), self.tmpSize)))

    def measurement_href(self):
        """Path of the main image inside measurements/, as packaged."""
        return os.path.relpath(self.image_file, self.EO_FOLDER).replace(os.sep, "/")

    def writeQuicklook(self, destPath):
        """Write the overview PNG at destPath, from the visual asset when the
        item carries one (8-bit RGB, used as delivered), else from the main
        image: red/green/blue bands, 2-98 percentile stretch per band over the
        valid (non-zero) pixels. No-data pixels become transparent. The
        smallest internal overview of at least OVERVIEW_MAX_SIZE pixels is
        read, when the GeoTIFF has any (Planet delivers COGs)."""
        import tifffile
        from PIL import Image

        source = self.visual_file or self.image_file
        is_visual = source == self.visual_file
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

        if is_visual and data.dtype == np.uint8 and bands >= 3:
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

    def buildTypeCode(self, processInfo):
        level = self.native_level
        xml_level = self.xml_text('EarthObservationMetaData', 'productType')
        if xml_level is not None:
            xml_level = xml_level.upper()
            if xml_level not in PROCESSING_LEVEL:
                raise Exception("unsupported PlanetScope native level: '%s' in %s"
                                % (xml_level, self.xml_file))
            # the asset name fixes ortho vs basic; the XML can only refine a
            # basic product between L1A and L1B
            if xml_level != level:
                if {level, xml_level} == {'L1A', 'L1B'}:
                    level = xml_level
                    self.typecode = 'L1AAB__MS_' if level == 'L1A' else 'L1BAB__MS_'
                else:
                    raise Exception("native level mismatch: asset %s says %s, XML %s says %s"
                                    % (os.path.basename(self.image_file), level,
                                       os.path.basename(self.xml_file), xml_level))
        self.native_level = level

        bands = self.num_bands
        xml_bands = self.xml_text('ProductInformation', 'numBands')
        if xml_bands is not None and self.xml_is_main_image_own() and int(xml_bands) != bands:
            raise Exception("band count mismatch: asset %s says %d, XML says %s"
                            % (os.path.basename(self.image_file), bands, xml_bands))

        mode = OPERATIONAL_MODE[bands]
        if mode not in ALLOWED_MODES[self.typecode]:
            raise Exception("operational mode %s not allowed for product type %s"
                            % (mode, self.typecode))

        self.metadata.setMetadataPair(NUM_BANDS, bands)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, PROCESSING_LEVEL[level])
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)
        print(("TYPECODE SET TO: %s (mode %s, level %s)" % (self.typecode, mode, level)))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")

        self.metadata = met
        met.setMetadataPair(ITEM_ID, self.item_id)
        met.setMetadataPair(ITEM_TYPE, self.item_type)

        # sensing times: the XML validity period, else the item acquisition
        # instant; a missing end is set to the beginning (spec Table 11)
        acquired = normalise_utc(self.prop('acquired'))
        start = normalise_utc(self.xml_text('validTime', 'TimePeriod', 'beginPosition')) or acquired
        # the XML often gives whole seconds: take the item's milliseconds
        # when both name the same second
        if acquired and start and start[:19] == acquired[:19]:
            start = acquired
        stop = normalise_utc(self.xml_text('validTime', 'TimePeriod', 'endPosition')) or start
        if stop and start and stop < start:
            stop = start
        if start is None:
            raise Exception("no acquisition time in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date: when Planet published the item
        processed = normalise_utc(self.prop('published') or self.prop('updated'))
        if processed is None:
            raise Exception("no 'published' / 'updated' date in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, processed)

        # package creation date (spec Table 6): now, the conversion time
        created = normalise_utc(datetime.now(timezone.utc).isoformat())
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # instrument -> platform
        instrument = self.prop('instrument') or self.xml_text('Instrument', 'shortName')
        if instrument not in PLATFORM_MAP:
            raise Exception("unknown PlanetScope instrument: '%s'" % instrument)
        met.setMetadataPair(INSTRUMENT_ID, instrument)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, instrument)
        satellite = self.prop('satellite_id') or self.xml_text('Platform', 'serialIdentifier')
        if satellite is not None:
            met.setMetadataPair(metadata.METADATA_SATELLITE, str(satellite))

        # orbit direction
        orbit_direction = (self.xml_text('Acquisition', 'orbitDirection') or '').upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid or missing orbit direction: '%s' in %s"
                            % (orbit_direction, self.xml_file))
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        # processor (lineage step 0)
        processor_name = self.xml_text('ProcessingInformation', 'processorName')
        processor_version = self.xml_text('ProcessingInformation', 'processorVersion')
        if processor_name is None or processor_version is None:
            raise Exception("missing processorName / processorVersion in %s" % self.xml_file)
        met.setMetadataPair(PROCESSOR_NAME, processor_name)
        met.setMetadataPair(PROCESSOR_VERSION, processor_version)

        self.buildTypeCode(processInfo)

        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the native item size; the base pipeline would
        # fill the eoSIP size here, so mark it as the other converters do
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # resolution: the delivered pixel size, else the ground sample distance
        resolution = self.prop('pixel_resolution', self.prop('gsd'))
        if resolution is None:
            resolution = self.xml_text('ProductInformation', 'columnGsd')
        if resolution is None or float(resolution) <= 0:
            raise Exception("invalid or missing resolution in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, float(resolution))

        # sun angles: item properties, else the asset XML
        sun_azimuth = self.prop('sun_azimuth', self.xml_text('Acquisition', 'illuminationAzimuthAngle'))
        sun_elevation = self.prop('sun_elevation', self.xml_text('Acquisition', 'illuminationElevationAngle'))
        if sun_azimuth is None or sun_elevation is None:
            raise Exception("missing sun azimuth / elevation in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, float(sun_azimuth))
        met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, float(sun_elevation))

        # incidence angle: the asset XML, else the item view angle (the
        # off-nadir angle, the closest figure the item properties carry)
        incidence = self.xml_text('Acquisition', 'incidenceAngle')
        if incidence is None:
            incidence = self.prop('view_angle')
        if incidence is None:
            raise Exception("missing incidence angle in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, float(incidence))

        # cloud cover, percent: cloud_percent (0-100), else cloud_cover (0-1);
        # optional (spec Table 19), left out when the item has neither
        cloud = self.prop('cloud_percent')
        if cloud is None and self.prop('cloud_cover') is not None:
            cloud = float(self.prop('cloud_cover')) * 100.0
        if cloud is not None:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, round(float(cloud), 2))

        # CRS of a geo-referenced product (spec Table 16, mandatory if present)
        epsg = self.xml_text('spatialReferenceSystem', 'epsgCode')
        if epsg is not None:
            met.addLocalAttribute("referenceSystemIdentifier",
                                  "http://www.opengis.net/def/crs/EPSG/0/%d" % int(epsg))

        met.addLocalAttribute("nativeDataFile", self.measurement_href())
        met.addLocalAttribute("measurementsMediaType", media_type_of(self.image_file))

        print(("## resolution=%s; sun az/el=%s/%s; incidence=%s; cloud=%s"
               % (resolution, sun_azimuth, sun_elevation, incidence, cloud)))

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint from the item GeoJSON geometry: the Polygon exterior ring
        as delivered (closed, counter-clockwise as RFC 7946 wants). A
        MultiPolygon is replaced by the bounding box of all its rings, since
        the specialization allows a Polygon only."""
        geometry = self.item.get('geometry') or {}
        gtype = geometry.get('type')
        coords = geometry.get('coordinates')
        if gtype == 'Polygon' and coords:
            ring = [[float(p[0]), float(p[1])] for p in coords[0]]
        elif gtype == 'MultiPolygon' and coords:
            points = [p for polygon in coords for p in polygon[0]]
            lons = [float(p[0]) for p in points]
            lats = [float(p[1]) for p in points]
            ring = [[min(lons), min(lats)], [max(lons), min(lats)],
                    [max(lons), max(lats)], [min(lons), max(lats)]]
        else:
            raise Exception("no Polygon / MultiPolygon footprint in %s" % self.path)

        if ring[0] != ring[-1]:
            ring.append(list(ring[0]))
        # shoelace on lon/lat: positive area = counter-clockwise
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
        if area < 0:
            ring.reverse()
        if len(ring) < 4:
            raise Exception("degenerate footprint in %s" % self.path)

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
