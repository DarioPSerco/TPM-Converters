# -*- coding: cp1252 -*-
#
# this class represent a pleiades product: the Airbus DIMAP delivery ZIP
#
# The ZIP holds one DIMAP document (DIM_PHR1*.XML) per component: one for a
# panchromatic, multispectral or pansharpened product, two (P + MS) for a
# bundle. Every component is read on its own, so a bundle gets one
# acquisitionParameters entry, one measurements link and one overview per
# component ("EOPF-EOS Specialization for PLEIADES products" 1.01).
#
import os
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.product_directory import Product_Directory

# custom metadata keys (mission-local, like PlanetScope's)
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# DIMAP DATASET_TYPE -> (product type level part, processingLevel (spec
# Table 18), native processedLevel code (spec Table 19))
LEVELS = {'RASTER_SENSOR': ('L1APRI', '1A', 'L1A'),
          'RASTER_PROJECTED': ('L2_PRO', '2', 'L2'),
          'RASTER_ORTHO': ('L3_ORT', '3', 'L3')}

# DIMAP SPECTRAL_PROCESSING (before any -N / -X colour variant) -> component kind
SPECTRAL_KINDS = {'P': 'PAN', 'MS': 'MS', 'PMS': 'PSH'}

# spec Table 2: the product types and the operational mode of each kind.
# Table 1 spells the bundle types L2_BNDLPRO / L3_BNDLORT, Table 2 and the
# example L2_PRO_BDL / L3_ORT_BDL: the latter, consistent with the other
# types, is used.
PRODUCT_TYPES = {'L1APRI_PAN', 'L3_ORT_PAN', 'L1APRI_MS_', 'L3_ORT_MS_',
                 'L1APRI_PSH', 'L2_PRO_PSH', 'L3_ORT_PSH',
                 'L1APRI_BDL', 'L2_PRO_BDL', 'L3_ORT_BDL'}
OPERATIONAL_MODE = {'PAN': 'PAN', 'MS': 'MS', 'PSH': 'MS'}

# spec Tables 15 / 16, in metres. The PSH NIR row of Table 15 repeats the
# VNIR bounds (480-820 nm), an edit left-over: the NIR band of the MS rows
# (775-915 nm) is used.
VNIR = ('VNIR', ((480e-09, 820e-09),))
VIS = ('VIS', ((450e-09, 530e-09), (510e-09, 590e-09), (620e-09, 700e-09)))
NIR = ('NIR', ((775e-09, 915e-09),))
SPECTRAL_RANGES = {'PAN': (VNIR,), 'MS': (VIS, NIR), 'PSH': (VNIR, VIS, NIR)}

# bundle components in the example's order, with their overview suffix
BUNDLE_ORDER = ('MS', 'PAN')
BUNDLE_PREVIEW_SUFFIX = {'MS': '_MS', 'PAN': '_PAN'}

OVERVIEW_MAX_SIZE = 1000

# DIMAP DATA_FILE_FORMAT -> measurements link type, from the EOF-EOS schema
# link-types thesaurus: it has no image/jp2 (octet-stream is used), and its
# only GeoTIFF entry is the cloud-optimized profile, which a DIMAP GeoTIFF
# is not (plain image/tiff is used)
MEDIA_TYPES = {'image/jp2': 'application/octet-stream', 'image/tiff': 'image/tiff'}


def normalise_utc(value):
    """DIMAP datetime ('...Z', with or without fraction; PRODUCTION_DATE has
    no 'Z' but is UTC) -> RFC 3339 UTC with milliseconds
    (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$", str(value).strip())
    if not match:
        raise Exception("unexpected Pleiades datetime format: '%s'" % value)
    date, time, frac = match.groups()
    return "%sT%s.%sZ" % (date, time, (frac or "").ljust(3, "0")[:3])


def wavelengths(kind):
    """spec Tables 15 / 16 rows of the component kind: one entry per
    spectral range, start / end the outer bounds of its bands,
    discreteWavelengths the band centres (the example's encoding)."""
    return [{
        "spectralRange": name,
        "startWavelength": min(b[0] for b in bands),
        "endWavelength": max(b[1] for b in bands),
        "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
    } for name, bands in SPECTRAL_RANGES[kind]]


def crs_uri(code):
    """DIMAP PROJECTED_CRS_CODE (urn:ogc:def:crs:EPSG::32644) -> the OGC
    http URI the spec asks for (http://www.opengis.net/def/crs/EPSG/0/32644)."""
    match = re.match(r"^urn:ogc:def:crs:EPSG:[^:]*:(\d+)$", code or "")
    if match:
        return "http://www.opengis.net/def/crs/EPSG/0/%s" % match.group(1)
    if code and code.isdigit():
        return "http://www.opengis.net/def/crs/EPSG/0/%s" % code
    return None


def _text(node, path):
    found = node.find(path)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Product_Pleiades(Product_Directory):

    #
    METADATA_PREFIX = 'DIM_PHR1'
    PREVIEW_PREFIX = 'PREVIEW_PHR1'
    STRIP_PREFIX = 'STRIP_DS_PHR1'

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        # one DIMAP document per component (two in a bundle)
        self.metContentName = []
        self.metContent = []
        self.previewContentName = []
        # LINEAGE/STRIP_DS_* documents, by path inside the ZIP: they carry the orbit
        self.stripContent = {}
        self.components = []
        if self.debug != 0:
            print(" init class Product_Pleiades")

    #
    # read matadata file
    #
    def getMetadataInfo(self, index=0):
        pass

    #
    # extract the pleiades interresting piece in working folder:
    # - DIMAP metadata xml
    # - preview images
    # and keep the lineage strip documents in memory
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        if self.debug != 0:
            print(" will extract directory product '%s' to path: %s" % (self.path, folder))

        self.EXTRACTED_PATH = folder
        self.contentList = []
        self.isPleiades = False
        with zipfile.ZipFile(self.path) as z:
            for n, name in enumerate(z.namelist()):
                if self.debug != 0:
                    print("  extract[%d]:%s" % (n, name))
                base = posixpath.basename(name).upper()
                keep = False
                if base.startswith(self.METADATA_PREFIX) and base.endswith('.XML'):  # metadata
                    self.metContentName.append(name)
                    self.metContent.append(z.read(name))
                    keep = True
                elif base.startswith(self.PREVIEW_PREFIX) and base.endswith('.JPG'):  # preview
                    self.previewContentName.append(name)
                    keep = True
                elif base.startswith(self.STRIP_PREFIX) and base.endswith('.XML'):  # lineage strip
                    self.stripContent[name] = z.read(name)
                if keep and dont_extract != True:
                    dest = os.path.join(folder, name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as outfile:
                        outfile.write(z.read(name))
                self.contentList.append(name)

                # pleaides test
                if base.startswith('IMG_PHR1'):
                    self.isPleiades = True

        if not self.isPleiades:
            raise Exception("is not a pleiades product")

    #
    #
    #
    def extractMetadata(self, met=None):
        if met is None:
            raise Exception("metadata is None")
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")
        self.metadata = met

        components = [self.parseComponent(name, data)
                      for name, data in zip(self.metContentName, self.metContent)]
        self.components = self.orderComponents(components)
        first = self.components[0]

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

        # native processing date, and package creation date (spec Table 6): now
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, first['productionDate'])
        created = normalise_utc(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f'))
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # platform: <MMM> of the package name is the 'Pl' of METADATA_PLATFORM
        # (cfg) + the first character of the mission index
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, first['missionIndex'])
        met.addLocalAttribute("platformShortName", "Pleiades-%s" % first['missionIndex'])

        self.buildTypeCode()

        if self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL) != '1A':
            # spec Table 17: mandatory for a geo-referenced product
            if first['crs'] is None:
                raise Exception("geo-referenced product without a projected CRS: %s" % first['name'])
            met.addLocalAttribute("referenceSystemIdentifier", first['crs'])

        met.addLocalAttribute("components", [{
            "operationalMode": OPERATIONAL_MODE[c['kind']],
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
    # one DIMAP document -> one component
    #
    def parseComponent(self, name, data):
        root = ET.fromstring(data)
        dim_dir = posixpath.dirname(name)

        spectral = _text(root, 'Processing_Information/Product_Settings/SPECTRAL_PROCESSING')
        kind = SPECTRAL_KINDS.get((spectral or '').split('-')[0])
        if kind is None:
            raise Exception("unsupported SPECTRAL_PROCESSING '%s' in %s" % (spectral, name))
        dataset_type = _text(root, 'Dataset_Identification/DATASET_TYPE')
        if dataset_type not in LEVELS:
            raise Exception("unsupported DATASET_TYPE '%s' in %s" % (dataset_type, name))

        strip = root.find('Dataset_Sources/Source_Identification/Strip_Source')
        if strip is None:
            raise Exception("no Strip_Source in %s" % name)
        mission_index = _text(strip, 'MISSION_INDEX')
        if mission_index not in ('1A', '1B'):
            raise Exception("unknown Pleiades MISSION_INDEX '%s' in %s" % (mission_index, name))

        # sensing times: the located geometric values (top, center, bottom of
        # the scene), else the strip imaging instant; a missing end is the
        # beginning (spec Table 11)
        located = root.findall('Geometric_Data/Use_Area/Located_Geometric_Values')
        times = sorted(normalise_utc(_text(l, 'TIME')) for l in located if _text(l, 'TIME'))
        if times:
            begin, end = times[0], times[-1]
        else:
            imaging_date = _text(strip, 'IMAGING_DATE')
            imaging_time = _text(strip, 'IMAGING_TIME')
            if imaging_date is None or imaging_time is None:
                raise Exception("no acquisition time in %s" % name)
            begin = end = normalise_utc("%sT%s" % (imaging_date, imaging_time))

        # angles: the scene center values (spec Table 13 asks for the mean);
        # each is written only when present
        center = next((l for l in located if _text(l, 'LOCATION_TYPE') == 'Center'),
                      located[0] if located else None)
        angles = {}
        if center is not None:
            for key, path in (('illuminationAzimuthAngle', 'Solar_Incidences/SUN_AZIMUTH'),
                              ('illuminationElevationAngle', 'Solar_Incidences/SUN_ELEVATION'),
                              ('acrossTrackIncidenceAngle', 'Acquisition_Angles/INCIDENCE_ANGLE_ACROSS_TRACK'),
                              ('alongTrackIncidenceAngle', 'Acquisition_Angles/INCIDENCE_ANGLE_ALONG_TRACK')):
                value = _float(_text(center, path))
                if value is not None:
                    angles[key] = value

        # resolution: the product resampling spacing, else the mean ground
        # sample distance at the scene center
        resolution = _float(_text(root, 'Processing_Information/Product_Settings/Sampling_Settings/RESAMPLING_SPACING'))
        if resolution is None and center is not None:
            gsd = [_float(_text(center, 'Ground_Sample_Distance/GSD_ACROSS_TRACK')),
                   _float(_text(center, 'Ground_Sample_Distance/GSD_ALONG_TRACK'))]
            gsd = [g for g in gsd if g is not None]
            if gsd:
                resolution = sum(gsd) / len(gsd)

        production = normalise_utc(_text(root, 'Product_Information/Delivery_Identification/PRODUCTION_DATE'))
        if production is None:
            raise Exception("no PRODUCTION_DATE in %s" % name)

        orbit_number, orbit_direction = self.orbitOf(root, name)

        return {
            'name': name,
            'kind': kind,
            'datasetType': dataset_type,
            'missionIndex': mission_index,
            'begin': begin,
            'end': end,
            'angles': angles,
            'resolution': resolution,
            'productionDate': production,
            'orbitNumber': orbit_number,
            'orbitDirection': orbit_direction,
            'crs': crs_uri(_text(root, 'Coordinate_Reference_System/Projected_CRS/PROJECTED_CRS_CODE')),
            'ring': self.footprintOf(root, name),
            'measurement': self.measurementOf(root, name, dim_dir),
            'preview': self.previewOf(root, name, dim_dir),
            'previewSuffix': '',
        }

    #
    # orbit number and direction: from the component's LINEAGE/STRIP_DS_*
    # document (the DIMAP product document does not carry them)
    #
    def orbitOf(self, root, name):
        dim_dir = posixpath.dirname(name)
        for comp in root.iter('COMPONENT_PATH'):
            href = comp.get('href', '')
            if not posixpath.basename(href).upper().startswith(self.STRIP_PREFIX):
                continue
            strip_name = posixpath.normpath(posixpath.join(dim_dir, href))
            if strip_name not in self.stripContent:
                continue
            strip = ET.fromstring(self.stripContent[strip_name])
            ephemeris = 'Acquisition_Configuration/Platform_Configuration/Ephemeris_Configuration/'
            number = _text(strip, ephemeris + 'ACQUISITION_ORBIT_NUMBER')
            direction = (_text(strip, ephemeris + 'ACQUISITION_ORBIT_DIRECTION') or '').upper()
            if number is None or direction not in ('ASCENDING', 'DESCENDING'):
                raise Exception("invalid or missing orbit in %s" % strip_name)
            return int(number), direction
        raise Exception("can not find the PLEIADES LINEAGE strip of %s" % name)

    #
    # footprint: the Dataset_Extent vertices, as a closed GeoJSON ring
    # [[lon, lat], ...], counterclockwise (RFC 7946 section 3.1.6)
    #
    def footprintOf(self, root, name):
        ring = []
        for vertex in root.findall('Dataset_Content/Dataset_Extent/Vertex'):
            lon = _float(_text(vertex, 'LON'))
            lat = _float(_text(vertex, 'LAT'))
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
    # measurements link (spec Table 21): the component image inside the
    # unpacked delivery; a tiled image has no single file, its DIMAP
    # document (which lists the tiles) is linked instead
    #
    def measurementOf(self, root, name, dim_dir):
        fmt = _text(root, 'Raster_Data/Data_Access/DATA_FILE_FORMAT')
        files = [f.get('href') for f in root.findall('Raster_Data/Data_Access/Data_Files/Data_File/DATA_FILE_PATH')]
        files = [posixpath.normpath(posixpath.join(dim_dir, f)) for f in files if f]
        missing = [f for f in files if f not in self.contentList]
        if not files or missing:
            raise Exception("image file(s) of %s not in the delivery: %s" % (name, missing or 'none listed'))
        if len(files) > 1:
            return {"href": name, "type": "application/xml"}
        return {"href": files[0], "type": MEDIA_TYPES.get(fmt, 'application/octet-stream')}

    #
    # the component quicklook (DATASET_QL_PATH)
    #
    def previewOf(self, root, name, dim_dir):
        ql = root.find('Dataset_Identification/DATASET_QL_PATH')
        if ql is not None and ql.get('href'):
            path = posixpath.normpath(posixpath.join(dim_dir, ql.get('href')))
            if path in self.previewContentName:
                return path
        # no quicklook reference: the only preview of the component folder
        candidates = [p for p in self.previewContentName if posixpath.dirname(p) == dim_dir]
        if len(candidates) == 1:
            return candidates[0]
        raise Exception("can not find the preview of %s" % name)

    #
    # one component, or a P + MS bundle in the example's order (MS first)
    #
    def orderComponents(self, components):
        if len(components) == 1:
            return components
        kinds = sorted(c['kind'] for c in components)
        if kinds != sorted(BUNDLE_ORDER):
            raise Exception("unsupported Pleiades component set: %s (only P + MS bundles)"
                            % ", ".join(c['kind'] for c in components))
        if len({c['datasetType'] for c in components}) != 1:
            raise Exception("bundle components with different DATASET_TYPE")
        components = sorted(components, key=lambda c: BUNDLE_ORDER.index(c['kind']))
        for c in components:
            c['previewSuffix'] = BUNDLE_PREVIEW_SUFFIX[c['kind']]
        return components

    #
    # spec Table 2:
    # L1APRI_PAN / L3_ORT_PAN                (spectral processing P)
    # L1APRI_MS_ / L3_ORT_MS_                (spectral processing MS)
    # L1APRI_PSH / L2_PRO_PSH / L3_ORT_PSH   (spectral processing PMS)
    # L1APRI_BDL / L2_PRO_BDL / L3_ORT_BDL   (bundle: P + MS)
    #
    def buildTypeCode(self):
        first = self.components[0]
        level, processing_level, level_code = LEVELS[first['datasetType']]
        kind = 'BDL' if len(self.components) > 1 else first['kind']
        typecode = "%s_%s" % (level, kind.ljust(3, '_'))
        if typecode not in PRODUCT_TYPES:
            raise Exception("buildTypeCode; product type %s not in the specialization (%s, %s)"
                            % (typecode, first['datasetType'], kind))

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, processing_level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE,
                                      ",".join(OPERATIONAL_MODE[c['kind']] for c in self.components))
        print("TYPECODE SET TO: %s (level %s)" % (typecode, processing_level))

    #
    # write one overview PNG per component next to the manifest, named
    # <EO name><suffix>.PNG as the manifest previews hrefs (section 4)
    #
    def writeQuicklooks(self, out_dir, eo_product_name):
        from PIL import Image
        written = []
        for c in self.components:
            src = os.path.join(self.EXTRACTED_PATH, c['preview'])
            dest = os.path.join(out_dir, "%s%s.PNG" % (eo_product_name, c['previewSuffix']))
            with Image.open(src) as im:
                im.thumbnail((OVERVIEW_MAX_SIZE, OVERVIEW_MAX_SIZE))
                im.save(dest, format="PNG")
            written.append(dest)
        return written

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
