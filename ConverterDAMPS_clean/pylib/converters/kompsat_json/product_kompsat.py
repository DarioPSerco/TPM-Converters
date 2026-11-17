"""This class represents a KOMPSAT-1 / KOMPSAT-2 native product.

The entry file is the ASCII AUX metadata <image stem>.txt of the product (of
the PAN component for a KOMPSAT-2 bundle). Layout, naming and the AUX keys
read: see kompsat_files.py and test/fixtures/SYNTHETIC_FIXTURE_NOTE.md.

Supported product types (EOPF-EOS specialization for KOMPSAT, Tables 1, 2):

L1BORT_PAN: KOMPSAT-1 EOC, PAN, 6.6 m                      processing level 1B
L1_OPT_BDL: KOMPSAT-2 MSC level 1R bundle, PAN 1 m + MS4B 4 m   processing level 1
L1_GEO_BDL: KOMPSAT-2 MSC level 1G bundle, PAN 1 m + MS4B 4 m   processing level 1

The native format is not described by the specialization and no real product
has been converted yet: see test/fixtures/SYNTHETIC_FIXTURE_NOTE.md.
"""
import os
import re
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.product_directory import Product_Directory

from kompsat_json import kompsat_files as F

__version__ = '1.0.0'

# custom metadata keys (mission-local)
PLATFORM_SHORT_NAME = 'platform_short_name'
INSTRUMENT_SHORT_NAME = 'instrument_short_name'
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# satellite number -> (platform short name (Table 8), instrument (Table 9),
# <MMM> platform id)
SATELLITES = {
    1: ("KOMPSAT-1", "EOC", "1"),
    2: ("KOMPSAT-2", "MSC", "2"),
}

# (satellite, native level) -> (product type, processingLevel (Table 18),
# processedLevel code (Table 19))
PRODUCT_TYPES = {
    (1, "L1B"): ("L1BORT_PAN", "1B", "L1B"),
    (2, "1R"): ("L1_OPT_BDL", "1", "L1R"),
    (2, "1G"): ("L1_GEO_BDL", "1", "L1G"),
}

# Table 2: resolution in metres per satellite and operational mode
RESOLUTIONS = {(1, "PAN"): 6.6, (2, "PAN"): 1.0, (2, "MS4B"): 4.0}

# Table 15/16, in metres, grouped by spectralRange
WAVELENGTHS = {
    (1, "PAN"): [("VNIR", [(510e-9, 730e-9)])],
    (2, "PAN"): [("VNIR", [(500e-9, 900e-9)])],
    (2, "MS4B"): [("VIS", [(450e-9, 520e-9), (520e-9, 600e-9), (630e-9, 690e-9)]),
                  ("NIR", [(760e-9, 900e-9)])],
}

# fixed by Table 17 (the only allowed value)
REFERENCE_SYSTEM = "http://www.opengis.net/def/crs/EPSG/0/4326"

IMAGE_EXTS = (".tif", ".tiff")
BROWSE_RE = re.compile(r"(_br|_browse|_ql|_quicklook)\.(jpe?g|png|tif|tiff)$", re.IGNORECASE)

# zero-based (red, green, blue) indices in a 4-band MS image: B, G, R, NIR
MS_RGB = (2, 1, 0)
# per-band MS images, in (red, green, blue) order
MS_BAND_RGB = ("M3", "M2", "M1")

OVERVIEW_MAX_SIZE = 1000

SATELLITE_RE = re.compile(r"(?:KOMPSAT|KOMSAT|K)[-_ ]?0*([0-9])(?![0-9A-Z])", re.IGNORECASE)
CORNER_RE = re.compile(r"(?:^|_)(TL|TR|BR|BL|UL|UR|LR|LL)(?:_|$)")
CORNER_ALIAS = {"UL": "TL", "UR": "TR", "LR": "BR", "LL": "BL"}
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?")


# -- value parsing --------------------------------------------------------

def first_number(value):
    """First number in an AUX value ('33.3 deg' -> 33.3), or None."""
    match = NUMBER_RE.search(str(value or ""))
    return float(match.group()) if match else None


def parse_utc(date_text, time_text=None):
    """AUX date / time -> RFC 3339 UTC with milliseconds. Accepts a full
    datetime in date_text ('2010-06-07T04:41:08.5Z'), or a date (YYYYMMDD,
    YYYY-MM-DD, YYYY/MM/DD) plus a time (hh:mm:ss[.f] or hhmmss[.f])."""
    if not date_text:
        return None
    text = str(date_text).strip().upper().rstrip("Z")
    match = re.match(r"^(\d{4})[-/]?(\d{2})[-/]?(\d{2})(?:[T ](.+))?$", text)
    if not match:
        raise Exception("unexpected KOMPSAT date format: '%s'" % date_text)
    year, month, day, inline_time = match.groups()
    clock = (inline_time or str(time_text or "")).strip().upper().rstrip("Z")
    if not clock:
        raise Exception("no time of day for KOMPSAT date '%s'" % date_text)
    tmatch = re.match(r"^(\d{2}):?(\d{2}):?(\d{2})(?:\.(\d+))?$", clock)
    if not tmatch:
        raise Exception("unexpected KOMPSAT time format: '%s'" % clock)
    hh, mm, ss, frac = tmatch.groups()
    micro = int((frac or "")[:6].ljust(6, "0"))
    parsed = datetime(int(year), int(month), int(day), int(hh), int(mm), int(ss), micro,
                      tzinfo=timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (parsed.microsecond // 1000)


def name_time(yymmddhhmmss):
    """MSC file name time token -> RFC 3339 UTC (two-digit years are 19xx
    from 90 on: KOMPSAT-1 was launched in 1999)."""
    yy = int(yymmddhhmmss[:2])
    year = 1900 + yy if yy >= 90 else 2000 + yy
    return parse_utc("%04d%s" % (year, yymmddhhmmss[2:6]), yymmddhhmmss[6:])


def find_value(aux, *candidates, tokens=None, exclude=()):
    """Value of the first candidate key present; else of the first key (sorted)
    holding every token and none of the excluded ones."""
    for key in candidates:
        if aux.get(key):
            return aux[key]
    if tokens:
        for key in sorted(k for k in aux if "." not in k):
            if all(t in key for t in tokens) and not any(e in key for e in exclude):
                return aux[key]
    return None


def acquisition_time(aux, which):
    """Start ('START') or stop ('END') of sensing from the AUX keys, or None."""
    for prefix in ("AUX_STRIP_ACQ", "AUX_IMAGE_ACQ", "AUX_ACQ", "AUX_ACQUISITION"):
        stamp = find_value(aux, "%s_%s_UT" % (prefix, which), "%s_%s_TIME" % (prefix, which),
                           "%s_%s" % (prefix, which))
        if stamp is None:
            continue
        if re.match(r"^\d{4}[-/]?\d{2}[-/]?\d{2}[T ]", stamp.strip()):
            return parse_utc(stamp)
        day = find_value(aux, "%s_DATE_UT" % prefix, "%s_DATE" % prefix)
        if day:
            return parse_utc(day, stamp)
    return None


def daylight_direction(start, lon):
    """Orbit direction of a KOMPSAT pass from its local solar time, for AUX
    files without a direction key. KOMPSAT-1 and KOMPSAT-2 fly sun-synchronous
    orbits with the descending node in the morning (about 10:50 local time),
    so a daylight pass (06:00-18:00 local) is DESCENDING, a night one
    ASCENDING. None when start or lon is missing."""
    if not start or lon is None:
        return None
    moment = datetime.strptime(start[:19], "%Y-%m-%dT%H:%M:%S")
    local_hours = (moment.hour + moment.minute / 60.0 + lon / 15.0) % 24.0
    return "DESCENDING" if 6.0 <= local_hours < 18.0 else "ASCENDING"


def processing_time(aux):
    """Native processing time from AUX_IMAGE_<level>_PROCESSED_UT keys
    (yyyymmddhhmmss[.ss], all zeros when the stage did not run): the latest
    stage wins. None when no such key holds a date."""
    found = []
    for key, value in aux.items():
        if "." in key or not re.match(r"^AUX_IMAGE_L\w+_PROCESSED_UT$", key):
            continue
        match = re.match(r"^(\d{8})(\d{6}(?:\.\d+)?)$", str(value).strip())
        if match and int(match.group(1)) > 0:
            found.append(parse_utc(match.group(1), match.group(2)))
    return max(found) if found else None


def satellite_number(aux, entry_name):
    """1 or 2 from AUX_SATELLITE_NAME, else the sensor, else the file name."""
    name = find_value(aux, "AUX_SATELLITE_NAME", "AUX_SATELLITE", "AUX_SPACECRAFT_NAME")
    if name:
        match = SATELLITE_RE.search(name)
        if match:
            number = int(match.group(1))
            if number not in SATELLITES:
                raise Exception("unsupported satellite '%s': KOMPSAT-1 and -2 only" % name)
            return number
        if "KOMPSAT" in name.upper() or "KOMSAT" in name.upper():
            raise Exception("unsupported satellite '%s': KOMPSAT-1 and -2 only" % name)
    sensor = (find_value(aux, "AUX_SATELLITE_SENSOR", "AUX_SENSOR_NAME", "AUX_SENSOR") or "").upper()
    base = os.path.basename(str(entry_name)).upper()
    for number, (_, instrument, _) in SATELLITES.items():
        if sensor.startswith(instrument) or base.startswith(instrument + "_"):
            return number
    raise Exception("unknown KOMPSAT satellite (AUX_SATELLITE_NAME '%s') for %s" % (name, entry_name))


def corner_ring(aux):
    """Footprint corners from the AUX keys as a [lon, lat] ring TL, TR, BR,
    BL (not closed), or None. Corner keys carry TL/TR/BR/BL (or UL/UR/LR/LL)
    and LAT/LON; decimal values only (keys with DEG/MIN/SEC parts skipped).
    A LATLONG key (real KOMPSAT-2 AUX, e.g. ``AUX_IMAGE_TL_LATLONG_DEG
    -14.868 35.712``) holds both, latitude first."""
    corners = {}
    # decimal-degree keys (..._DEC) first, so they win over other forms
    for key in sorted((k for k in aux if "." not in k), key=lambda k: (not k.endswith("_DEC"), k)):
        if "PIXEL" in key or "LINE" in key or key.endswith(("_MIN", "_SEC")):
            continue
        match = CORNER_RE.search(key.replace("AUX_", "_", 1))
        if not match:
            continue
        if "LATLONG" in key:
            numbers = NUMBER_RE.findall(aux[key])
            if len(numbers) == 2:
                corner = CORNER_ALIAS.get(match.group(1), match.group(1))
                corners.setdefault(corner, {}).setdefault("lat", float(numbers[0]))
                corners[corner].setdefault("lon", float(numbers[1]))
            continue
        axis = "lat" if "LAT" in key else "lon" if "LON" in key else None
        value = first_number(aux[key])
        if axis is None or value is None or re.search(r"\d\s+\d", aux[key]):
            continue
        corner = CORNER_ALIAS.get(match.group(1), match.group(1))
        corners.setdefault(corner, {}).setdefault(axis, value)
    if not all(c in corners and len(corners[c]) == 2 for c in ("TL", "TR", "BR", "BL")):
        return None
    ring = [[corners[c]["lon"], corners[c]["lat"]] for c in ("TL", "TR", "BR", "BL")]
    for lon, lat in ring:
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise Exception("footprint corner out of range: lon=%s lat=%s" % (lon, lat))
    return ring


# -- image helpers ----------------------------------------------------------

def _read_reduced(path, max_size=OVERVIEW_MAX_SIZE * 2):
    """Image as (rows, cols, bands), decimated so its long side is at most
    about max_size (the overview needs no more)."""
    import tifffile
    data = tifffile.imread(path)
    if data.ndim == 2:
        data = data[:, :, np.newaxis]
    elif data.ndim == 3 and data.shape[0] < data.shape[-1] and data.shape[0] <= 8:
        data = np.moveaxis(data, 0, -1)  # planar (bands, rows, cols)
    step = max(1, int(np.ceil(max(data.shape[:2]) / float(max_size))))
    return data[::step, ::step, :]


def _stretch(band, valid):
    values = band[valid]
    out = np.zeros(band.shape, dtype=np.uint8)
    if values.size == 0:
        return out
    low, high = np.percentile(values, (2.0, 98.0))
    if high <= low:
        high = low + 1.0
    return (np.clip((band - low) / (high - low), 0, 1) * 255).astype(np.uint8)


class Component:
    """One part of the product: PAN, or MS4B (KOMPSAT-2 bundle)."""

    def __init__(self, mode, metadata_file, images):
        self.mode = mode                    # 'PAN' or 'MS4B'
        self.metadata_file = metadata_file  # AUX .txt, or None
        self.images = images                # absolute paths, sorted
        self.aux = F.parse_aux(metadata_file) if metadata_file else {}


class Product_Kompsat(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        name = os.path.basename(self.path)
        if os.path.splitext(name)[1].lower() != F.METADATA_EXT:
            raise Exception("not a KOMPSAT AUX metadata file (<image stem>.txt): %s" % path)
        self.aux = F.parse_aux(self.path)
        if not any(k.startswith("AUX_") for k in self.aux):
            raise Exception("no AUX_ keys in %s: not a KOMPSAT AUX metadata file" % path)

        self.EO_FOLDER = F.product_root(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.files = F.product_files(self.path, self.EO_FOLDER)
        self.satellite = satellite_number(self.aux, name)
        self.name_fields = F.msc_name(name)
        self.preview_path = None
        self.tmpSize = 0
        self.typecode = None
        self.components = []
        self.browse_file = next((f for f in self.files if BROWSE_RE.search(f)), None)
        self._select_components()

        if self.debug != 0:
            print(" init class Product_Kompsat (%s)" % name)

    # -- components -------------------------------------------------------

    def _images(self, files):
        return [f for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS
                and not BROWSE_RE.search(f)]

    def _select_components(self):
        if self.satellite == 1:
            images = self._images(self.files)
            if not images:
                raise Exception("no KOMPSAT-1 image (.tif) next to %s; files: %s"
                                % (self.path, ", ".join(os.path.basename(f) for f in self.files)))
            self.components = [Component("PAN", self.path, images)]
            return

        if self.name_fields is None or self.name_fields["mode"] not in F.PAN_MODES:
            raise Exception("KOMPSAT-2 entry must be the PAN metadata "
                            "(MSC_<time>_<orbit>_<path/row>PN|PP<nn>_<1R|1G>.txt): %s" % self.path)
        by_mode = {}
        for f in self.files:
            mode = F.msc_name(f)["mode"]
            by_mode.setdefault(mode, []).append(f)
        pan_images = self._images([f for m in F.PAN_MODES for f in by_mode.get(m, [])])
        ms_files = [f for m in F.MS_MODES for f in by_mode.get(m, [])]
        ms_images = sorted(self._images(ms_files))
        if not pan_images:
            raise Exception("KOMPSAT-2 bundle without PAN image: %s" % self.path)
        if not ms_images:
            raise Exception("KOMPSAT-2 bundle without MS component (MS or M1..M4 images) for %s"
                            % self.path)
        ms_meta = next((f for f in ms_files if F.is_aux_metadata(f)), None)
        self.components = [Component("PAN", self.path, pan_images),
                           Component("MS4B", ms_meta, ms_images)]

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
        print((" #### native product %s: %d file(s), %d bytes"
               % (os.path.basename(self.path), len(self.files), self.tmpSize)))

    def measurement_href(self):
        """Path of the (PAN) image inside measurements/, as packaged."""
        image = self.components[0].images[0]
        return os.path.relpath(image, self.EO_FOLDER).replace(os.sep, "/")

    def writeQuicklook(self, destPath):
        """Write the overview PNG at destPath: the native browse when the
        product carries one; else rendered from the MS component (red, green,
        blue bands, 2-98 percentile stretch); else from the PAN image (grey).
        No-data (zero) pixels become transparent."""
        from PIL import Image

        if self.browse_file:
            with Image.open(self.browse_file) as im:
                image = im.convert("RGBA")
            source = self.browse_file
        else:
            ms = next((c for c in self.components if c.mode == "MS4B"), None)
            if ms is not None:
                rgb_planes, source = self._ms_planes(ms)
            else:
                source = self.components[0].images[0]
                grey = _read_reduced(source)[:, :, 0].astype("float64")
                rgb_planes = [grey, grey, grey]
            valid = np.any(np.dstack(rgb_planes) > 0, axis=-1)
            rgb = np.dstack([_stretch(p, valid) for p in rgb_planes])
            alpha = np.where(valid, 255, 0).astype(np.uint8)
            image = Image.fromarray(np.dstack([rgb, alpha]))
        image.thumbnail((OVERVIEW_MAX_SIZE, OVERVIEW_MAX_SIZE), Image.Resampling.LANCZOS)
        image.save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### overview written: %s (from %s)" % (destPath, os.path.basename(source))))
        return destPath

    def _ms_planes(self, ms):
        """(red, green, blue) float planes of the MS component and the source
        file: one 4-band image (B, G, R, NIR), or one image per band (M1..M4)."""
        per_band = {F.msc_name(f)["mode"]: f for f in ms.images}
        if all(b in per_band for b in MS_BAND_RGB):
            planes = [_read_reduced(per_band[b])[:, :, 0].astype("float64") for b in MS_BAND_RGB]
            rows = min(p.shape[0] for p in planes)
            cols = min(p.shape[1] for p in planes)
            return [p[:rows, :cols] for p in planes], per_band[MS_BAND_RGB[0]]
        source = ms.images[0]
        data = _read_reduced(source)
        if data.shape[-1] < 3:
            raise Exception("cannot build an RGB overview from %d band(s): %s"
                            % (data.shape[-1], source))
        return [data[:, :, i].astype("float64") for i in MS_RGB], source

    # -- metadata ---------------------------------------------------------

    def _native_level(self):
        if self.satellite == 1:
            return "L1B"
        level = self.name_fields["level"]
        aux_level = (find_value(self.aux, "AUX_PROCESSING_LEVEL", "AUX_PRODUCT_LEVEL") or "").upper()
        aux_match = re.search(r"1[RG]", aux_level)
        if aux_match and aux_match.group() != level:
            raise Exception("processing level of the file name (%s) and AUX (%s) differ: %s"
                            % (level, aux_level, self.path))
        return level

    def buildTypeCode(self, processInfo):
        key = (self.satellite, self._native_level())
        if key not in PRODUCT_TYPES:
            raise Exception("unsupported KOMPSAT product: satellite %s, level %s" % key)
        self.typecode, processing_level, level_code = PRODUCT_TYPES[key]
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, processing_level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE,
                                      self.components[0].mode)
        print(("TYPECODE SET TO: %s" % self.typecode))

    def _times(self, aux, fallback_start=None):
        start = acquisition_time(aux, "START") or fallback_start
        stop = acquisition_time(aux, "END") or start
        if start and stop < start:
            stop = start
        return start, stop

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met
        aux = self.aux

        # platform (Tables 1, 8, 9): <MMM> = KO + satellite number
        platform, instrument, platform_id = SATELLITES[self.satellite]
        met.setMetadataPair(PLATFORM_SHORT_NAME, platform)
        met.setMetadataPair(INSTRUMENT_SHORT_NAME, instrument)
        met.setMetadataPair(metadata.METADATA_PLATFORM, platform)
        met.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, "KO")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform_id)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, instrument)

        # sensing times (Table 11); the MSC name carries the start as well
        fallback = name_time(self.name_fields["time"]) if self.name_fields else None
        start, stop = self._times(aux, fallback)
        if start is None:
            raise Exception("no acquisition start time in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date, else the beginning of sensing (Table 18)
        processed = None
        for prefix in ("AUX_PROCESSING", "AUX_PRODUCTION", "AUX_PRODUCT_GENERATION", "AUX_GENERATION"):
            day = find_value(aux, "%s_DATE_UT" % prefix, "%s_DATE" % prefix)
            if day:
                processed = parse_utc(day, find_value(aux, "%s_TIME_UT" % prefix, "%s_TIME" % prefix)
                                      or "00:00:00")
                break
        processed = processed or processing_time(aux)
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, processed or start)

        # package creation date (Table 6): now, the conversion time
        created = parse_utc(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f"))
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # orbit (Table 12, mandatory)
        orbit = find_value(aux, "AUX_ORBIT_NUMBER", "AUX_REVOLUTION_NUMBER", "AUX_ORBIT")
        orbit = orbit or (self.name_fields or {}).get("orbit")
        if first_number(orbit) is None:
            raise Exception("no orbit number in %s" % self.path)
        orbit_number = int(first_number(orbit))
        met.setMetadataPair(metadata.METADATA_ORBIT, orbit_number)
        direction = (find_value(aux, "AUX_ORBIT_DIRECTION", "AUX_PASS_DIRECTION", "AUX_ORBIT_PASS",
                                tokens=("DIRECTION",), exclude=("SCAN", "LOOK", "SUN"))
                     or "").strip().upper()
        direction = {"A": "ASCENDING", "ASC": "ASCENDING", "D": "DESCENDING",
                     "DESC": "DESCENDING"}.get(direction, direction)
        if not direction:
            # real AUX files carry no direction key: derive it from the
            # local solar time at the footprint centre
            ring = next((r for r in (corner_ring(c.aux or aux) for c in self.components) if r), None)
            lon = sum(p[0] for p in ring) / len(ring) if ring else None
            direction = daylight_direction(start, lon) or ""
        if direction not in ("ASCENDING", "DESCENDING"):
            raise Exception("invalid or missing orbit direction: '%s' in %s" % (direction, self.path))
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, direction)

        self.buildTypeCode(processInfo)
        self.refineMetadata(processInfo, start, stop, orbit_number, direction)
        self.extractFootprint(processInfo)

    def _angles(self, aux):
        """Table 13 angles found in an AUX dict (all optional)."""
        angles = {}
        for key, tokens in (("illuminationAzimuthAngle", ("SUN", "AZIMUTH")),
                            ("illuminationElevationAngle", ("SUN", "ELEVATION"))):
            value = first_number(find_value(aux, tokens=tokens))
            if value is not None:
                angles[key] = value
        for key, side, tilt in (("alongTrackIncidenceAngle", "ALONG", "AUX_TILT_ANGLE_PITCH_DEG"),
                                ("acrossTrackIncidenceAngle", "ACROSS", "AUX_TILT_ANGLE_ROLL_DEG")):
            for word in ("INCIDENCE", "VIEW", "TILT", "OFF_NADIR"):
                value = first_number(find_value(aux, tokens=(side, word), exclude=("GSD", "PIXEL")))
                if value is not None:
                    angles[key] = value
                    break
            else:
                value = first_number(aux.get(tilt))
                if value is not None:
                    angles[key] = value
        return angles

    def refineMetadata(self, processInfo, start, stop, orbit_number, direction):
        met = self.metadata

        # the manifest reports the native product size; the base pipeline would
        # fill the eoSIP size here, so mark it as the other converters do
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        components = []
        for comp in self.components:
            aux = comp.aux or self.aux
            begin, end = self._times(aux, start) if comp.aux else (start, stop)
            angles = self._angles(aux) or self._angles(self.aux)
            if self.satellite == 1 and not angles:
                raise Exception("no acquisition angle in %s (mandatory for KOMPSAT-1, Table 10)"
                                % self.path)
            components.append({
                "mode": comp.mode,
                "begin": begin,
                "end": end,
                "resolution": RESOLUTIONS[(self.satellite, comp.mode)],
                "orbitNumber": orbit_number,
                "orbitDirection": direction,
                "angles": angles,
                "wavelengths": wavelengths(self.satellite, comp.mode),
            })
        met.addLocalAttribute("components", components)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, components[0]["resolution"])

        # cloud cover, percent (Table 20, left out when unavailable)
        cloud = first_number(find_value(self.aux, "AUX_CLOUD_STATUS", "AUX_CLOUD_COVER",
                                        "AUX_CLOUD_COVERAGE", tokens=("CLOUD",)))
        if cloud is not None and 0.0 <= cloud <= 100.0:
            met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, round(cloud, 2))

        met.addLocalAttribute("referenceSystemIdentifier", REFERENCE_SYSTEM)
        met.addLocalAttribute("nativeDataFile", self.measurement_href())
        met.addLocalAttribute("measurementsMediaType", "image/tiff")

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint from the AUX corner coordinates (PAN component, else MS),
        closed and counter-clockwise as RFC 7946 wants."""
        ring = None
        for comp in self.components:
            ring = corner_ring(comp.aux or self.aux)
            if ring:
                break
        if ring is None:
            raise Exception("no footprint corners (TL/TR/BR/BL latitude/longitude) in %s" % self.path)
        ring.append(list(ring[0]))
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


def wavelengths(satellite, mode):
    """Table 15/16 rows: outer bounds per spectral range, band means as
    discreteWavelengths."""
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands),
        "endWavelength": max(b[1] for b in bands),
        "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
    } for spectral_range, bands in WAVELENGTHS[(satellite, mode)]]
