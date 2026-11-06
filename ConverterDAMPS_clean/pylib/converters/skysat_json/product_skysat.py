"""This class represents a SkySat native product (one Planet item).

The entry file is the item metadata `<item id>_metadata.json` (a GeoJSON
Feature: geometry + `properties`). The item assets sit next to it, either in
the same folder (Orders API delivery, possibly shared by several items) or in
per-asset sub-folders (legacy Data API download). The native product unit is
therefore every file under the entry folder whose name starts with the item
id - the same rule the packager uses to fill measurements/. Planet ships no
asset XML for SkySat: every metadata value comes from the item JSON, the CRS
from the GeoTIFF GeoKeys.

Supported product types (EOPF-EOS specialization for SkySat, Tables 2 and 3):

SkySatScene item, keyed by the main image asset (first hit in SCENE_ASSETS):
L3_ORT_PSH: <id>_pansharpened.tif                           4-band pansharpened
L3_ORT_MS_: <id>_analytic_SR.tif / _analytic.tif / _analytic_dn.tif
L3_ORTVMS_: <id>_visual.tif                                 3-band visual
L3_ORT_PAN: <id>_panchromatic.tif / _panchromatic_dn.tif
L1BBDN_MSP: <id>_basic_panchromatic[_dn].tif (+ _basic_analytic[_dn].tif)
L1BBDN_MS_: <id>_basic_analytic[_dn].tif
L1ABDN_PAN: <id>_basic_l1a_panchromatic_dn.tif              super resolution

SkySatCollect item -> SYNORT_BDL, one component per image kind found
(BUNDLE_COMPONENTS): 3-band pansharpened (visual), 4-band pansharpened,
4-band analytic, panchromatic. Each component gets its own
acquisitionParameters entry, measurements link and overview.
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

METADATA_SUFFIX = "_metadata.json"

ITEM_TYPE_SCENE = "SkySatScene"
ITEM_TYPE_COLLECT = "SkySatCollect"
BUNDLE_TYPECODE = 'SYNORT_BDL'

# custom metadata keys (mission-local, like PlanetScope's)
ITEM_ID = 'item_id'
ITEM_TYPE = 'item_type'
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# image kinds: band count and the zero-based (red, green, blue) band indices
# for the overview (analytic / pansharpened are B,G,R,N; visual is R,G,B)
IMAGE_KINDS = {
    'PSH3B': (3, (0, 1, 2)),
    'PSH4B': (4, (2, 1, 0)),
    'MS4B': (4, (2, 1, 0)),
    'PAN': (1, (0, 0, 0)),
}

# SkySatScene main image assets, in order of preference: (regex on the file
# name after the item id, product type, native level, image kind). The
# regexes are anchored at the item id, so '_analytic' never matches
# '_basic_analytic'.
SCENE_ASSETS = (
    (r"_pansharpened\.tiff?$", 'L3_ORT_PSH', 'L3B', 'PSH4B'),
    (r"_analytic_sr\.tiff?$", 'L3_ORT_MS_', 'L3B', 'MS4B'),
    (r"_analytic\.tiff?$", 'L3_ORT_MS_', 'L3B', 'MS4B'),
    (r"_analytic_dn\.tiff?$", 'L3_ORT_MS_', 'L3B', 'MS4B'),
    (r"_visual\.tiff?$", 'L3_ORTVMS_', 'L3B', 'PSH3B'),
    (r"_panchromatic\.tiff?$", 'L3_ORT_PAN', 'L3B', 'PAN'),
    (r"_panchromatic_dn\.tiff?$", 'L3_ORT_PAN', 'L3B', 'PAN'),
    (r"_basic_panchromatic(_dn)?\.tiff?$", 'L1BBDN_MSP', 'L1B', 'PAN'),
    (r"_basic_analytic(_dn)?\.tiff?$", 'L1BBDN_MS_', 'L1B', 'MS4B'),
    (r"_basic_l1a_panchromatic_dn\.tiff?$", 'L1ABDN_PAN', 'L1A', 'PAN'),
)
# L1BBDN_MSP is the panchromatic + 4-band basic scene: the basic analytic
# image, when delivered too, is a second measurements link
MSP_COMPANION = r"_basic_analytic(_dn)?\.tiff?$"

# visual assets are colour-balanced 8-bit RGB, used as-is for the overview
VISUAL_ASSET = r"_visual\.tiff?$"

# spec Table 3 / Table 16, in this order (the specialization example's):
# (component, preview suffix, asset regexes in preference order,
#  operationalMode, spectral ranges)
BUNDLE_COMPONENTS = (
    ('PSH3B', '_PSH3B', (r"_visual\.tiff?$",), 'MS', ('VNIR', 'VIS')),
    ('PSH4B', '_PSH4B', (r"_pansharpened\.tiff?$",), 'MS', ('VNIR', 'VIS', 'NIR')),
    ('MS4B', '_MS', (r"_analytic_sr\.tiff?$", r"_analytic\.tiff?$", r"_analytic_dn\.tiff?$"),
     'MS4B', ('VIS', 'NIR')),
    ('PAN', '_PAN', (r"_panchromatic\.tiff?$", r"_panchromatic_dn\.tiff?$"), 'PAN', ('VNIR',)),
)

# spec Table 2 (operationalMode) and Table 15 (spectral ranges) per
# non-bundle product type
PRODUCT_TYPES = {
    'L1ABDN_PAN': ('PAN', ('VNIR',)),
    'L1BBDN_MS_': ('MS4B', ('VIS', 'NIR')),
    'L1BBDN_MSP': ('MS', ('VNIR', 'VIS', 'NIR')),
    'L3_ORTVMS_': ('MS', ('VIS',)),
    'L3_ORT_PSH': ('MS', ('VNIR', 'VIS', 'NIR')),
    'L3_ORT_MS_': ('MS', ('VIS', 'NIR')),
    'L3_ORT_PAN': ('PAN', ('VNIR',)),
}

# spec Table 11
OPERATIONAL_MODES = ('MS3B', 'MS4B', 'MS', 'PAN')

# spec Tables 15 and 16, in metres: band (start, end) per spectral range
SPECTRAL_RANGES = {
    'VNIR': [(450e-9, 900e-9)],
    'VIS': [(450e-9, 515e-9), (515e-9, 595e-9), (605e-9, 695e-9)],
    'NIR': [(740e-9, 900e-9)],
}

# native level -> processingLevel (spec Table 18); the bundle is ortho
PROCESSING_LEVEL = {'L1A': '1A', 'L1B': '1B', 'L3B': '3', 'SYN': '3'}

OVERVIEW_MAX_SIZE = 1000

MEDIA_TYPES = {".tif": "image/tiff", ".tiff": "image/tiff"}


def normalise_utc(value):
    """Planet datetime ('...Z' with microseconds, or '+00:00' with or without
    fraction) -> RFC 3339 UTC with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:?\d{2})?$", text)
    if not match:
        raise Exception("unexpected SkySat datetime format: '%s'" % value)
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
        raise Exception("not a SkySat item metadata file (<item id>%s): %s"
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


def wavelengths(spectral_ranges):
    """spec Tables 15 / 16 rows: one entry per spectral range, start / end
    the outer bounds of its bands, discreteWavelengths the band centres (the
    specialization example's encoding)."""
    out = []
    for name in spectral_ranges:
        bands = SPECTRAL_RANGES[name]
        out.append({
            "spectralRange": name,
            "startWavelength": min(b[0] for b in bands),
            "endWavelength": max(b[1] for b in bands),
            "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
        })
    return out


def epsg_of(tif_path):
    """EPSG code from the GeoTIFF GeoKeys (projected, else geographic), or
    None when the image carries none (basic scenes are not geo-referenced)."""
    import tifffile

    with tifffile.TiffFile(tif_path) as tif:
        keys = tif.geotiff_metadata or {}
    for key in ('ProjectedCSTypeGeoKey', 'GeographicTypeGeoKey'):
        value = keys.get(key)
        try:
            code = int(value)
        except (TypeError, ValueError):
            continue
        # 32767 is the GeoTIFF 'user-defined' code, not an EPSG one
        if 0 < code < 32767:
            return code
    return None


class Product_Skysat(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        self.item_id = item_id_of(self.path)
        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.preview_paths = []
        self.tmpSize = 0

        with open(self.path, 'r', encoding='utf-8') as fd:
            self.item = json.load(fd)
        if not isinstance(self.item, dict) or 'properties' not in self.item:
            raise Exception("not a SkySat item metadata (no 'properties'): %s" % path)
        self.properties = self.item['properties']
        self.item_type = str(self.properties.get('item_type') or '')
        if self.item_type not in (ITEM_TYPE_SCENE, ITEM_TYPE_COLLECT):
            raise Exception("unsupported SkySat item_type: '%s' in %s" % (self.item_type, path))

        self.files = item_files(self.EO_FOLDER, self.item_id)
        self.typecode = None
        self.native_level = None
        # one dict per acquisitionParameters entry / measurements image /
        # overview: kind, file (absolute), operationalMode, spectral ranges,
        # preview suffix ('' outside the bundle)
        self.components = []
        self.measurement_files = []
        if self.item_type == ITEM_TYPE_COLLECT:
            self._select_bundle_assets()
        else:
            self._select_scene_assets()

        if self.debug != 0:
            print(" init class Product_Skysat (%s, %s)" % (self.item_id, self.item_type))

    # -- assets -----------------------------------------------------------

    def _match(self, pattern):
        """Item files whose name after the item id matches pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [f for f in self.files if regex.match(os.path.basename(f)[len(self.item_id):])]

    def _no_image(self, wanted):
        return Exception("no supported SkySat %s image asset for item %s (%s) in %s; files: %s"
                         % (wanted, self.item_id, self.item_type, self.EO_FOLDER,
                            ", ".join(os.path.basename(f) for f in self.files) or "none"))

    def _select_scene_assets(self):
        for pattern, typecode, level, kind in SCENE_ASSETS:
            hits = self._match(pattern)
            if hits:
                image = hits[0]
                self.typecode, self.native_level = typecode, level
                break
        else:
            raise self._no_image("scene")

        mode, ranges = PRODUCT_TYPES[self.typecode]
        # the overview of an ortho scene comes from its visual asset when
        # the item carries one, as for PlanetScope
        visual = self._match(VISUAL_ASSET) if level == 'L3B' else []
        self.components = [{'kind': kind, 'file': image, 'overview': visual[0] if visual else image,
                            'operationalMode': mode, 'spectralRanges': ranges, 'suffix': ''}]
        self.measurement_files = [image]
        if self.typecode == 'L1BBDN_MSP':
            companion = self._match(MSP_COMPANION)
            if companion:
                self.measurement_files.append(companion[0])

    def _select_bundle_assets(self):
        self.typecode, self.native_level = BUNDLE_TYPECODE, 'SYN'
        for kind, suffix, patterns, mode, ranges in BUNDLE_COMPONENTS:
            for pattern in patterns:
                hits = self._match(pattern)
                if hits:
                    self.components.append({'kind': kind, 'file': hits[0], 'overview': hits[0],
                                            'operationalMode': mode, 'spectralRanges': ranges,
                                            'suffix': suffix})
                    break
        if not self.components:
            raise self._no_image("collect (visual / pansharpened / analytic / panchromatic)")
        self.measurement_files = [c['file'] for c in self.components]

    def prop(self, name, default=None):
        value = self.properties.get(name)
        return default if value is None else value

    # -- product lifecycle ------------------------------------------------

    def afterProductDone(self):
        pass

    def getMetadataInfo(self):
        pass

    # JSON-only mode: the base ingester browse stage is disabled; the preview
    # PNGs are written next to the manifest by writeQuicklooks().
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

    def href_of(self, path):
        """Path of an item file inside measurements/, as packaged."""
        return os.path.relpath(path, self.EO_FOLDER).replace(os.sep, "/")

    def overview_names(self, eo_name):
        """Overview file names: '<package name>.PNG', or for the bundle one
        '<package name>_<PSH3B|PSH4B|MS|PAN>.PNG' per component (spec
        section 4)."""
        return ["%s%s.PNG" % (eo_name, c['suffix']) for c in self.components]

    def writeQuicklooks(self, out_dir, eo_name):
        """Write every overview PNG in out_dir; return their paths."""
        paths = []
        for component, name in zip(self.components, self.overview_names(eo_name)):
            dest = os.path.join(out_dir, name)
            self.writeQuicklook(component, dest)
            paths.append(dest)
        self.preview_paths = paths
        return paths

    def writeQuicklook(self, component, destPath):
        """Write one overview PNG at destPath from the component overview
        source: an 8-bit RGB visual asset is used as delivered; otherwise the
        red/green/blue bands (the single band, grey, for a panchromatic
        image) get a 2-98 percentile stretch over the valid (non-zero)
        pixels. No-data pixels become transparent. The smallest internal
        overview of at least OVERVIEW_MAX_SIZE pixels is read, when the
        GeoTIFF has any (Planet delivers COGs)."""
        import tifffile
        from PIL import Image

        source = component['overview']
        is_visual = re.search(VISUAL_ASSET, os.path.basename(source), re.IGNORECASE) is not None

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
            if bands == 1:
                picked = data[:, :, [0, 0, 0]].astype('float64')
            elif bands >= 3:
                red, green, blue = IMAGE_KINDS[component['kind']][1] if bands == 4 else (0, 1, 2)
                picked = data[:, :, [red, green, blue]].astype('float64')
            else:
                raise Exception("cannot build an overview from %d band(s): %s" % (bands, source))
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
        print((" #### overview written: %s (from %s)" % (destPath, os.path.basename(source))))
        return destPath

    # -- metadata ---------------------------------------------------------

    def buildTypeCode(self, processInfo):
        for component in self.components:
            if component['operationalMode'] not in OPERATIONAL_MODES:
                raise Exception("operational mode %s not allowed (spec Table 11)"
                                % component['operationalMode'])
        # the main mode: the first component's (the only one outside the bundle)
        mode = self.components[0]['operationalMode']
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL,
                                      PROCESSING_LEVEL[self.native_level])
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, self.native_level)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)
        print(("TYPECODE SET TO: %s (mode %s, level %s, %d component(s))"
               % (self.typecode, mode, self.native_level, len(self.components))))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")

        self.metadata = met
        met.setMetadataPair(ITEM_ID, self.item_id)
        met.setMetadataPair(ITEM_TYPE, self.item_type)

        # sensing times: the item gives the acquisition instant only, so the
        # end equals the beginning
        start = normalise_utc(self.prop('acquired'))
        if start is None:
            raise Exception("no 'acquired' time in %s" % self.path)
        stop = start
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date (spec Table 18): when Planet published the item
        processed = normalise_utc(self.prop('published') or self.prop('updated'))
        if processed is None:
            raise Exception("no 'published' / 'updated' date in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, processed)

        # package creation date (spec Table 7): now, the conversion time
        created = normalise_utc(datetime.now(timezone.utc).isoformat())
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        satellite = self.prop('satellite_id')
        if satellite is not None:
            met.setMetadataPair(metadata.METADATA_SATELLITE, str(satellite))

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
        if resolution is None or float(resolution) <= 0:
            raise Exception("invalid or missing resolution (pixel_resolution / gsd) in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, float(resolution))

        sun_azimuth = self.prop('sun_azimuth')
        sun_elevation = self.prop('sun_elevation')
        if sun_azimuth is None or sun_elevation is None:
            raise Exception("missing sun_azimuth / sun_elevation in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, float(sun_azimuth))
        met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, float(sun_elevation))

        # across track incidence angle (spec Table 13): the item view angle,
        # the off-nadir angle, the only one the item properties carry
        incidence = self.prop('view_angle')
        if incidence is None:
            raise Exception("missing view_angle in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, float(incidence))

        # cloud cover, percent: cloud_percent (0-100), else cloud_cover (0-1);
        # optional (spec Table 20), left out when the item has neither
        cloud = self.prop('cloud_percent')
        if cloud is None and self.prop('cloud_cover') is not None:
            cloud = float(self.prop('cloud_cover')) * 100.0
        if cloud is not None:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, round(float(cloud), 2))

        # CRS of a geo-referenced (ortho) product (spec Table 17); basic
        # scenes are in the raw sensor frame and carry none
        epsg = None
        if self.native_level in ('L3B', 'SYN'):
            epsg = epsg_of(self.components[0]['file'])
            if epsg is not None:
                met.addLocalAttribute("referenceSystemIdentifier",
                                      "http://www.opengis.net/def/crs/EPSG/0/%d" % epsg)

        met.addLocalAttribute("components", [{
            "operationalMode": c['operationalMode'],
            "spectralRanges": list(c['spectralRanges']),
            "previewSuffix": c['suffix'],
        } for c in self.components])
        met.addLocalAttribute("measurements", [{
            "href": self.href_of(f),
            "type": media_type_of(f),
        } for f in self.measurement_files])

        print(("## resolution=%s; sun az/el=%s/%s; incidence=%s; cloud=%s; epsg=%s"
               % (resolution, sun_azimuth, sun_elevation, incidence, cloud, epsg)))

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
