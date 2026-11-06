"""This class represents a RADARSAT-1 native product in RADARSAT CEOS format.

A delivery is one folder per scene holding the CEOS file set, all with the
same stem:

- ``<stem>.vol``  volume directory (the entry file of the product)
- ``<stem>.sarl`` SAR leader file
- ``<stem>.sard`` SAR image data file
- ``<stem>.sart`` SAR trailer file
- ``<stem>.nvol`` null volume directory
- ``<stem>.txt``  scene description written by the distributor

Where each value is read:

- Data Set Summary record (leader, or trailer for SSG / ScanSAR products):
  product kind (SLC / SGF / SSG / SCN / SCW), orbit number and direction,
  polarisation, look side (sensor clock angle), incidence angle at scene
  centre, nominal range / azimuth resolution, line / pixel spacing;
- Processing Parameters record: sensing start / stop times (the scene
  description of a ScanSAR product can list them in reverse order);
- Map Projection record (SSG only): the UTM zone of the geocoded image;
- volume directory: the native processing date;
- scene description: the beam mode, the four corner coordinates (first image
  line first / last pixel, last image line first / last pixel) and the
  sensing times when the Processing Parameters record is absent (SSG).

The overview PNG is computed from the image data file (``.sard``): detected
products give the amplitude directly, SLC products the modulus of the complex
samples.

Supported product types (EOPF-EOS specialization for RADARSAT-1, Table 2):
L1_BM__SLC, L1_BM__SGF, L2_BM__SSG, L1_BSW_SLC, L1_BSW_SGF, L1_BMF_SLC,
L1_BMF_SGF, L1_BS__SGF, L1_SCN____, L1_SCW____.
"""
import os
import re
import struct
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

VOL_SUFFIX = ".vol"
LEADER_SUFFIX = ".sarl"
IMAGE_SUFFIX = ".sard"
TRAILER_SUFFIX = ".sart"
SCENE_SUFFIX = ".txt"

# CEOS record type codes (record header byte 6)
REC_DATA_SET_SUMMARY = 10
REC_MAP_PROJECTION = 20
REC_PROCESSING_PARAMETERS = 120

# the measurements link points at the CEOS image data file, a binary format
# with no registered media type
MEASUREMENTS_MEDIA_TYPE = "application/octet-stream"

# longest side of the overview PNG, in pixels
PREVIEW_MAX_SIZE = 1024

# custom metadata keys (mission-local, like COSMO-SkyMed's)
NATIVE_PRODUCT_KIND = 'native_product_kind'
BEAM_MODE = 'beam_mode'
PROCESSED_LEVEL_CODE = 'processed_level_code'

# scene description beam mode -> operationalMode (spec Table 2); ScanSAR
# products take their operationalMode from the product kind instead
BEAM_MAP = (
    ("SAR STANDARD", "BM"),
    ("SAR WIDE", "BSW"),
    ("SAR FINE", "BMF"),
    ("SAR EXTENDED LOW", "BS"),
)
SCANSAR_KINDS = ("SCN", "SCW")

# (native product kind, operationalMode) -> product type (spec Table 2)
TYPECODE_MAP = {
    ("SLC", "BM"): "L1_BM__SLC",
    ("SGF", "BM"): "L1_BM__SGF",
    ("SSG", "BM"): "L2_BM__SSG",
    ("SLC", "BSW"): "L1_BSW_SLC",
    ("SGF", "BSW"): "L1_BSW_SGF",
    ("SLC", "BMF"): "L1_BMF_SLC",
    ("SGF", "BMF"): "L1_BMF_SGF",
    ("SGF", "BS"): "L1_BS__SGF",
    ("SCN", "SCN"): "L1_SCN____",
    ("SCW", "SCW"): "L1_SCW____",
}

# native product kind -> processingLevel / processedLevel code (spec Tables
# 16-17): SSG is the only geocoded (level 2) product
LEVEL_MAP = {
    "SLC": ("1", "L1"),
    "SGF": ("1", "L1"),
    "SCN": ("1", "L1"),
    "SCW": ("1", "L1"),
    "SSG": ("2", "L2"),
}

MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
          "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

POLARISATIONS = ("HH", "HV", "VH", "VV")

WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"


def read_records(path):
    """{record type: first record of that type} of a CEOS file."""
    with open(path, 'rb') as fd:
        data = fd.read()
    records = {}
    offset = 0
    while offset + 12 <= len(data):
        length = struct.unpack('>I', data[offset + 8:offset + 12])[0]
        if length < 12:
            raise Exception("corrupt CEOS record at byte %d of %s" % (offset, path))
        records.setdefault(data[offset + 5], data[offset:offset + length])
        offset += length
    return records


def field(record, first, last):
    """CEOS field at 1-based inclusive byte positions, as stripped text."""
    return record[first - 1:last].decode('latin1').strip()


def float_field(record, first, last, name):
    text = field(record, first, last)
    try:
        return float(text)
    except ValueError:
        raise Exception("invalid CEOS field %s: '%s'" % (name, text))


def format_utc(value):
    """datetime -> RFC 3339 with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    return "%s.%03dZ" % (value.strftime("%Y-%m-%dT%H:%M:%S"), value.microsecond // 1000)


def parse_ceos_time(text):
    """CEOS 'YYYY-DDD-hh:mm:ss.sss' (day of year) -> datetime."""
    match = re.match(r"^(\d{4})-(\d{3})-(\d{2}):(\d{2}):(\d{2})\.(\d{3})$", text)
    if not match:
        raise Exception("unexpected CEOS time format: '%s'" % text)
    year, doy, hh, mm, ss, ms = (int(g) for g in match.groups())
    return datetime(year, 1, 1) + timedelta(days=doy - 1, hours=hh, minutes=mm,
                                            seconds=ss, milliseconds=ms)


def parse_scene_time(text):
    """Scene description 'JUL 01 1998 18:17:05.407' -> datetime."""
    match = re.match(r"^([A-Z]{3}) (\d{2}) (\d{4}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$", text.strip())
    if not match or match.group(1) not in MONTHS:
        raise Exception("unexpected scene description time format: '%s'" % text)
    month, day, year, hh, mm, ss, frac = match.groups()
    millis = int((frac + "000")[:3]) if frac else 0
    return datetime(int(year), MONTHS[month], int(day), int(hh), int(mm), int(ss), millis * 1000)


def parse_scene_description(text):
    """Scene description -> ({KEY: value}, [lat, lon] x 4 corners).

    The corners are listed as two blocks of latitudes then longitudes: first
    image line (first pixel, last pixel), then last image line (first pixel,
    last pixel)."""
    values = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Z#][A-Z#_ ]*?)\s{2,}(\S.*)$", line.strip())
        if match:
            values.setdefault(match.group(1), match.group(2).strip())

    corners = []
    pos = text.find("CORNER COORDINATES")
    if pos >= 0:
        dms = re.findall(r"(\d+)\D(\d+)'(\d+(?:\.\d+)?)\"\s*([NSEW])", text[pos:])
        degrees = []
        for deg, minutes, seconds, hemisphere in dms:
            value = int(deg) + int(minutes) / 60.0 + float(seconds) / 3600.0
            degrees.append(-value if hemisphere in "SW" else value)
        if len(degrees) == 8:
            lat1, lat2, lon1, lon2, lat3, lat4, lon3, lon4 = degrees
            corners = [(lat1, lon1), (lat2, lon2), (lat3, lon3), (lat4, lon4)]
    return values, corners


def image_layout(path):
    """Layout of a CEOS SAR image data file, from its file descriptor."""
    with open(path, 'rb') as fd:
        head = fd.read(12)
        descriptor_length = struct.unpack('>I', head[8:12])[0]
        fd.seek(0)
        descriptor = fd.read(descriptor_length)
    record_length = int(field(descriptor, 187, 192))
    pixels = int(field(descriptor, 249, 256))
    bytes_per_pixel = int(field(descriptor, 225, 228))
    sample_format = field(descriptor, 429, 432)
    if sample_format not in ("IU1", "IU2", "CI*4"):
        raise Exception("unsupported CEOS sample format '%s' in %s" % (sample_format, path))
    # ScanSAR descriptors leave the record count blank: use the file size
    lines = (os.path.getsize(path) - descriptor_length) // record_length
    prefix = record_length - pixels * bytes_per_pixel
    if lines <= 0 or pixels <= 0 or prefix < 0:
        raise Exception("inconsistent CEOS image layout in %s" % path)
    return {"descriptor_length": descriptor_length, "record_length": record_length,
            "lines": lines, "pixels": pixels, "prefix": prefix,
            "sample_format": sample_format}


def read_amplitude_line(fd, layout, line):
    fd.seek(layout["descriptor_length"] + line * layout["record_length"] + layout["prefix"])
    pixels = layout["pixels"]
    fmt = layout["sample_format"]
    if fmt == "IU1":
        return np.frombuffer(fd.read(pixels), dtype=np.uint8).astype(np.float32)
    if fmt == "IU2":
        return np.frombuffer(fd.read(pixels * 2), dtype='>u2').astype(np.float32)
    iq = np.frombuffer(fd.read(pixels * 4), dtype='>i2').astype(np.float32).reshape(-1, 2)
    return np.hypot(iq[:, 0], iq[:, 1])


def to_uint8(amplitude):
    """Linear 2-98 % stretch of the non-zero samples; zero (no data) stays black."""
    valid = amplitude > 0
    out = np.zeros(amplitude.shape, dtype=np.uint8)
    if not valid.any():
        return out
    low, high = np.percentile(amplitude[valid], (2, 98))
    if high <= low:
        high = low + 1.0
    scaled = np.clip((amplitude - low) / (high - low), 0, 1) * 254 + 1
    out[valid] = scaled[valid].astype(np.uint8)
    return out


class Product_Radarsat1(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        if not str(self.path).lower().endswith(VOL_SUFFIX):
            raise Exception("not a RADARSAT-1 CEOS volume directory (.vol): %s" % path)

        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.stem = os.path.splitext(os.path.basename(self.path))[0]
        self.preview_path = None
        self.tmpSize = 0

        self.leader_path = self._member(LEADER_SUFFIX)
        self.image_path = self._member(IMAGE_SUFFIX)
        self.scene_path = self._member(SCENE_SUFFIX)
        trailer = os.path.join(self.EO_FOLDER, self.stem + TRAILER_SUFFIX)
        self.trailer_path = trailer if os.path.isfile(trailer) else None

        with open(self.path, 'rb') as fd:
            self.volume = fd.read(360)
        leader = read_records(self.leader_path)
        trailer_records = read_records(self.trailer_path) if self.trailer_path else {}

        def record(code):
            return leader.get(code) or trailer_records.get(code)

        self.dss = record(REC_DATA_SET_SUMMARY)
        if self.dss is None:
            raise Exception("no Data Set Summary record in %s / %s"
                            % (self.leader_path, self.trailer_path))
        self.processing = record(REC_PROCESSING_PARAMETERS)
        self.map_projection = record(REC_MAP_PROJECTION)

        with open(self.scene_path, 'r', encoding='latin1') as fd:
            self.scene, self.corners = parse_scene_description(fd.read())

        if self.debug != 0:
            print(" init class Product_Radarsat1")

    def _member(self, suffix):
        path = os.path.join(self.EO_FOLDER, self.stem + suffix)
        if not os.path.isfile(path):
            raise FileNotFoundError("corrupt RADARSAT-1 native product (no %s file): %s"
                                    % (suffix, path))
        return path

    def scene_value(self, key):
        value = self.scene.get(key)
        if not value:
            raise Exception("missing '%s' in %s" % (key, self.scene_path))
        return value

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
        the CEOS files in place. Walk the delivery to get the size of what
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
        print((" #### native delivery: %d file(s), %d bytes"
               % (len(self.contentList), self.tmpSize)))

    def writeQuicklook(self, destPath):
        """Write the overview PNG computed from the image data file: lines
        sampled evenly, pixels averaged in bins, so the longest side is
        PREVIEW_MAX_SIZE and a pixel covers about the same ground distance in
        both directions. The image is flipped so that north is up and west is
        left, from the corner coordinates."""
        from PIL import Image

        layout = image_layout(self.image_path)
        lines, pixels = layout["lines"], layout["pixels"]
        line_spacing = float_field(self.dss, 1687, 1702, "line spacing")
        pixel_spacing = float_field(self.dss, 1703, 1718, "pixel spacing")
        if self.metadata.getMetadataValue(NATIVE_PRODUCT_KIND) == "SLC":
            # slant range spacing -> ground range spacing
            incidence = float(self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE))
            pixel_spacing /= np.sin(np.radians(incidence))
        along = lines * line_spacing
        across = pixels * pixel_spacing
        if along >= across:
            height = min(PREVIEW_MAX_SIZE, lines)
            width = max(1, min(pixels, int(round(height * across / along))))
        else:
            width = min(PREVIEW_MAX_SIZE, pixels)
            height = max(1, min(lines, int(round(width * along / across))))

        rows = np.linspace(0, lines - 1, height).round().astype(int)
        edges = np.linspace(0, pixels, width + 1).round().astype(int)[:-1]
        counts = np.diff(np.append(edges, pixels))
        image = np.zeros((height, width), dtype=np.float32)
        with open(self.image_path, 'rb') as fd:
            for i, line in enumerate(rows):
                amplitude = read_amplitude_line(fd, layout, line)
                image[i] = np.add.reduceat(amplitude, edges) / counts

        data = to_uint8(image)
        (lat1, lon1), (lat2, lon2), (lat3, lon3), (lat4, lon4) = self.corners
        if (lat3 + lat4) > (lat1 + lat2):
            data = data[::-1, :]
        # longitude difference wrapped to [-180, 180) for the antimeridian
        if ((lon2 + lon4) / 2 - (lon1 + lon3) / 2 + 180) % 360 - 180 < 0:
            data = data[:, ::-1]

        Image.fromarray(np.ascontiguousarray(data), 'L').save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### overview written: %s (%dx%d from %dx%d)"
               % (destPath, width, height, pixels, lines)))
        return destPath

    # -- metadata ---------------------------------------------------------

    def buildTypeCode(self, processInfo):
        scene_id = field(self.dss, 21, 36)
        match = re.match(r"^RSAT-1-SAR-([A-Z]{3})$", scene_id)
        if not match:
            raise Exception("unexpected RADARSAT-1 product identifier: '%s'" % scene_id)
        kind = match.group(1)
        if kind not in LEVEL_MAP:
            raise Exception("unsupported RADARSAT-1 product kind: '%s'" % kind)

        beam = self.scene_value("BEAM MODE")
        if kind in SCANSAR_KINDS:
            mode = kind
        else:
            mode = next((code for prefix, code in BEAM_MAP if beam.upper().startswith(prefix)), None)
            if mode is None:
                raise Exception("unsupported RADARSAT-1 beam mode: '%s'" % beam)
        typecode = TYPECODE_MAP.get((kind, mode))
        if typecode is None:
            raise Exception("unsupported RADARSAT-1 product: %s in beam mode '%s'" % (kind, beam))
        level, level_code = LEVEL_MAP[kind]

        self.metadata.setMetadataPair(NATIVE_PRODUCT_KIND, kind)
        self.metadata.setMetadataPair(BEAM_MODE, beam)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        print(("TYPECODE SET TO: %s (kind %s, beam '%s')" % (typecode, kind, beam)))

    def sensing_times(self):
        """(start, stop) datetimes: Processing Parameters record, else the
        scene description; returned in chronological order."""
        times = []
        if self.processing is not None:
            text = self.processing[:400].decode('latin1')
            times = [parse_ceos_time(t) for t in
                     re.findall(r"\d{4}-\d{3}-\d{2}:\d{2}:\d{2}\.\d{3}", text)[:2]]
        if len(times) != 2:
            times = [parse_scene_time(self.scene_value("SCENE START TIME")),
                     parse_scene_time(self.scene_value("SCENE STOP TIME"))]
        return min(times), max(times)

    def processing_time(self):
        """Native processing date: the volume directory creation date/time."""
        date, clock = field(self.volume, 113, 120), field(self.volume, 121, 128)
        if not re.match(r"^\d{8}$", date) or not re.match(r"^\d{6,8}$", clock):
            raise Exception("no creation date in the volume directory %s" % self.path)
        return datetime.strptime(date + clock[:6], "%Y%m%d%H%M%S")

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met

        # sensing times
        start, stop = self.sensing_times()
        start, stop = format_utc(start), format_utc(stop)
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # native processing date
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, format_utc(self.processing_time()))

        # package creation date (spec Table 6): now, the conversion time
        created = format_utc(datetime.now(timezone.utc))
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # orbit
        orbit = field(self.dss, 445, 452)
        if not orbit.isdigit():
            raise Exception("invalid orbit number: '%s'" % orbit)
        met.setMetadataPair(metadata.METADATA_ORBIT, int(orbit))
        orbit_direction = field(self.dss, 101, 116).upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid orbit direction: '%s'" % orbit_direction)
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        # polarisation: the channels named in the sensor identifier
        sensor_id = field(self.dss, 413, 444)
        channels = [p for p in POLARISATIONS if re.search(r"(?<![A-Z])%s(?![A-Z])" % p, sensor_id)]
        if not channels:
            raise Exception("no polarisation in the sensor identifier: '%s'" % sensor_id)
        met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, 'S' if len(channels) == 1 else 'D')
        met.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, ", ".join(channels))

        # look side: sensor clock angle +90 (right) / -90 (left)
        clock_angle = float_field(self.dss, 477, 484, "sensor clock angle")
        met.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION,
                            "RIGHT" if clock_angle > 0 else "LEFT")

        self.buildTypeCode(processInfo)
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the delivered package size; the base pipeline
        # would fill the eoSIP size here, so mark it as ICEYE does
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # nominal resolutions (range is slant range for SLC products)
        range_resolution = float_field(self.dss, 1351, 1366, "nominal range resolution")
        azimuth_resolution = float_field(self.dss, 1367, 1382, "nominal azimuth resolution")
        if range_resolution <= 0 or azimuth_resolution <= 0:
            raise Exception("invalid resolution: range=%s azimuth=%s"
                            % (range_resolution, azimuth_resolution))
        resolution = round(max(range_resolution, azimuth_resolution), 3)
        met.addLocalAttribute("rangeResolution", round(range_resolution, 3))
        met.addLocalAttribute("azimuthResolution", round(azimuth_resolution, 3))
        # single figure the spec also asks for: worst of the two directions
        met.addLocalAttribute("resolution", resolution)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)

        incidence = float_field(self.dss, 485, 492, "incidence angle at scene centre")
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, incidence)

        met.addLocalAttribute("referenceSystemIdentifier", self.reference_system())

        # the measurements link points at the image data file
        met.addLocalAttribute("nativeDataFile", os.path.basename(self.image_path))
        met.addLocalAttribute("measurementsMediaType", MEASUREMENTS_MEDIA_TYPE)

        print(("## resolution range=%s azimuth=%s; incidence=%s"
               % (range_resolution, azimuth_resolution, incidence)))

    def reference_system(self):
        """CRS URI: the UTM zone of the map projection record for the
        geocoded SSG product, WGS84 geographic for the other products (their
        footprint and the image record coordinates are geodetic)."""
        if self.metadata.getMetadataValue(NATIVE_PRODUCT_KIND) != "SSG":
            return WGS84
        if self.map_projection is None:
            raise Exception("no Map Projection record for the SSG product %s" % self.path)
        text = self.map_projection.decode('latin1')
        match = re.search(r"UNIVERSAL TRANSVERSE MERCATOR\s+(\d{1,4})\s+([\d.]+)\s+([\d.]+)", text)
        if not match or "WGS84" not in text:
            raise Exception("SSG map projection is not WGS84 UTM in %s" % self.leader_path)
        zone = int(match.group(1))
        false_northing = float(match.group(3))
        if not 1 <= zone <= 60:
            raise Exception("invalid UTM zone %d in %s" % (zone, self.leader_path))
        return "http://www.opengis.net/def/crs/EPSG/0/%d" % ((32700 if false_northing > 0 else 32600) + zone)

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint posList (lat lon pairs, CCW) from the scene description
        corners."""
        if len(self.corners) != 4:
            raise Exception("no corner coordinates in %s" % self.scene_path)
        first_first, first_last, last_first, last_last = self.corners
        ring = [first_first, first_last, last_last, last_first, first_first]
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
