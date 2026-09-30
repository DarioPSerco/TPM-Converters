"""JSON metadata emitter for WorldView products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps WorldView's own extraction (the metadata
dict populated by ``product_worldview.Product_Worldview.extractMetadata``),
declares the WorldView mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
WORLDVIEW PRODUCTS" 1.0 through its own placeholder template
(``feature_template_wv.json``). Unlike GeoEye-1/QuickBird-2, platformShortName and
instrumentShortName are supplied by the DYNAMIC layer: the WorldView mission
covers WV1/WV2/WV3/Legion, so platform identity varies per product. Which
layer fills a slot is the mission's choice — the generator merges uniformly.

Spec readings encoded here:
- wavelengths: Table 11 and the example spell the block ``wavelenghts``,
  Table 14 (which defines its content) spells ``wavelengths``; the plural is
  used, as for COSMO-SkyMed. One entry per spectralRange of Table 15:
  start/stop are the outer bounds of the range, discreteWavelengths the band
  centres. WorldView Legion MS4B is missing from Table 15: its B/G/R/N bands
  are taken from the Legion MS8B row (same values as WorldView-2/3 MS4B).
- lineage source: Table 18 is normative (``source[0].sourceCitation.title``),
  not the example (``source[0].citation``).
- cloudCover and referenceSystemIdentifier are written only when the native
  product carries them (Table 19; Table 16 makes the CRS mandatory only for
  L2AVRS_* and L3_* - a missing CRS there fails the conversion).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from worldview_json import __version__

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_wv.json"

# WorldView mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for WorldView",
                "reference": {"title": "EOPF-EOS Specialization for WorldView products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for WorldView",
                    "edition": __version__}},
            }]}],
        },
    },
}

# native instrument label (METADATA_INSTRUMENT) -> instrumentShortName
INSTRUMENT_SHORTNAME = {
    "WV60": "WorldView-60 Camera",
    "WV110": "WorldView-110 Camera",
    "SpaceView-110": "SpaceView-110 Camera",
    "WorldView Legion Camera": "WorldView Legion Camera",
}

# spec Table 15, in nm: (satellite, band set) -> [(spectralRange, [(start, stop), ...])]
_WV23_MS8B = [("VIS", [(400, 450), (450, 510), (510, 580), (585, 625), (630, 690)]),
              ("NIR", [(705, 745), (770, 895)]),
              ("IR", [(860, 1040)])]
_WV23_MS4B = [("VIS", [(450, 510), (510, 580), (630, 690)]),
              ("NIR", [(770, 895)])]
WAVELENGTHS_NM = {
    ("1", "PAN"): [("VNIR", [(450, 900)])],
    ("2", "PAN"): [("VNIR", [(450, 800)])],
    ("3", "PAN"): [("VNIR", [(450, 800)])],
    ("4", "PAN"): [("VNIR", [(450, 800)])],
    ("L", "PAN"): [("VNIR", [(450, 800)])],
    ("2", "MS8B"): _WV23_MS8B,
    ("3", "MS8B"): _WV23_MS8B,
    ("2", "MS4B"): _WV23_MS4B,
    ("3", "MS4B"): _WV23_MS4B,
    ("3", "SWIR"): [("SWIR", [(1195, 1225), (1550, 1590), (1640, 1680), (1710, 1750),
                              (2145, 2185), (2185, 2225), (2235, 2285), (2295, 2365)])],
    ("4", "MS4B"): [("VIS", [(450, 510), (510, 580), (655, 690)]),
                    ("NIR", [(780, 920)])],
    ("L", "MS8B"): [("VIS", [(400, 450), (450, 510), (510, 580), (585, 625), (630, 690)]),
                    ("VNIR", [(695, 715)]),
                    ("NIR", [(730, 750), (770, 895)])],
    # not in Table 15: the B/G/R/N bands of the Legion MS8B row
    ("L", "MS4B"): [("VIS", [(450, 510), (510, 580), (630, 690)]),
                    ("NIR", [(770, 895)])],
}

# spec Table 17: native level -> processingLevel ("3" for every other level)
PROCESSING_LEVEL = {"LV1B": "1B", "Stereo1B": "1B",
                    "LV2A": "2A", "Stereo2A": "2A", "StereoOR2A": "2A"}

# spec Table 16: product types that must carry referenceSystemIdentifier
CRS_MANDATORY = ("L2AVRS_PAN", "L2AVRS_MS_", "L3_MRO_PAN", "L3_MRP_MS_")


def _gv(met, key):
    v = met.getMetadataValue(key)
    if not met.valueExists(v):
        return None
    return v


def _norm_dt(s):
    """Normalise a datetime string to RFC 3339 with millisecond precision + Z."""
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$", s)
    if not m:
        return s
    base, frac = m.group(1), m.group(2)
    millis = (frac + "000")[:3] if frac else "000"
    return "%s.%sZ" % (base, millis)


def _polygon_coordinates(footprint):
    """footprint = 'lat lon lat lon ...' (closed ring) -> [[[lon, lat], ...]]."""
    toks = [t for t in str(footprint).split() if t != ""]
    ring = []
    for i in range(0, len(toks) - 1, 2):
        lat = float(toks[i])
        lon = float(toks[i + 1])
        ring.append([lon, lat])
    return [ring]


def _platform_short_name(met, is_legion):
    if is_legion:
        return "WorldView Legion"
    pid = _gv(met, M.METADATA_PLATFORM_ID)
    return "WorldView-%s" % pid if pid is not None else None


def _band_set(met):
    """PAN / MS4B / MS8B / SWIR from the native band count and bandId."""
    nb = _gv(met, "numberOfBands")
    try:
        nb = int(float(nb))
    except (TypeError, ValueError):
        return None
    if nb == 1:
        return "PAN"
    if nb in (3, 4):
        return "MS4B"
    if nb == 8:
        band_id = (_gv(met, "bandId") or "").replace('"', "")
        return "SWIR" if band_id == "All-S" else "MS8B"
    return None


def _operational_mode(met):
    """spec Table 11: PAN / MS4B / MS8B / STEREO. Stereo native levels give
    STEREO; the WorldView-3 SWIR band set is an MS8B mode (Table 3)."""
    if "Stereo" in (_processed_level(met) or ""):
        return "STEREO"
    band_set = _band_set(met)
    return "MS8B" if band_set == "SWIR" else band_set


def _wavelengths(met, is_legion):
    satellite = "L" if is_legion else _gv(met, M.METADATA_PLATFORM_ID)
    ranges = WAVELENGTHS_NM.get((satellite, _band_set(met)))
    if ranges is None:
        return None
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands) / 1e9,
        "stopWavelength": max(b[1] for b in bands) / 1e9,
        "discreteWavelengths": [(b[0] + b[1]) / 2 / 1e9 for b in bands],
    } for spectral_range, bands in ranges]


def _reference_system(met):
    """EPSG URI from the native map projection: WGS84 UTM -> 326zz/327zz,
    WGS84 geographic -> 4326. None when not derivable."""
    datum = (_gv(met, "datumName") or "").replace('"', "")
    proj = (_gv(met, "mapProjName") or "").replace('"', "")
    if datum != "WE":
        return None
    if proj == "UTM":
        zone = _gv(met, "mapZone")
        hemi = (_gv(met, "mapHemi") or "").replace('"', "")
        if zone is None or hemi not in ("N", "S"):
            return None
        code = (32600 if hemi == "N" else 32700) + int(zone)
    elif proj.startswith("Geographic"):
        code = 4326
    else:
        return None
    return "http://www.opengis.net/def/crs/EPSG/0/%d" % code


def _processing_level(met):
    level = _processed_level(met)
    return PROCESSING_LEVEL.get(level, "3") if level else None


def _processed_level(met):
    raw = _gv(met, M.METADATA_PROCESSING_LEVEL)
    if raw is None:
        return None
    return raw.replace("other: ", "").strip()


def build_layers(met, product, eo_product_name, native_product_name=None):
    """WorldView per-product dynamic values, from this mission's extraction."""
    is_legion = bool(getattr(product, "is_wv_legion", False))
    native_name = native_product_name or getattr(product, "origName", None) or eo_product_name
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

    resolution = _gv(met, M.METADATA_RESOLUTION)
    sun_az = _gv(met, M.METADATA_SUN_AZIMUTH)
    sun_el = _gv(met, M.METADATA_SUN_ELEVATION)
    cloud = _gv(met, M.METADATA_CLOUD_COVERAGE)
    if cloud is not None and str(cloud) == "-999":
        cloud = None
    instrument_native = _gv(met, M.METADATA_INSTRUMENT)
    size = getattr(product, "tmpSize", 0) or 0
    crs = _reference_system(met)
    if crs is None and typecode in CRS_MANDATORY:
        raise ValueError("referenceSystemIdentifier is mandatory for %s but the native "
                         "map projection gives none" % typecode)

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformShortName": _platform_short_name(met, is_legion)},
                "instrument": {"instrumentShortName":
                               INSTRUMENT_SHORTNAME.get(instrument_native, instrument_native)},
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _operational_mode(met),
                    "resolution": float(resolution) if resolution is not None else None,
                    "wavelengths": _wavelengths(met, is_legion),
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": float(sun_az) if sun_az is not None else None,
                        "illuminationElevationAngle": float(sun_el) if sun_el is not None else None,
                    },
                }],
            }],
            "productInformation": {
                "size": int(size),
                "cloudCover": float(cloud) if cloud is not None else None,
                "productType": typecode,
                "referenceSystemIdentifier": crs,
                "processingDate": created,
                "processingLevel": _processing_level(met),
                "resourceLineage": [{"processStep": [{
                    "stepDateTime": {"created": created},
                    "source": [{"sourceCitation": {"title": native_name},
                                "processedLevel": {"code": _processed_level(met)}}],
                    "output": [{"sourceCitation": {"title": "%s.ZIP" % eo_product_name}}],
                }]}],
            },
            "links": {
                "measurements": [{"href": "/measurements/%s" % native_name}],
                "preview": [{"href": "/preview/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
