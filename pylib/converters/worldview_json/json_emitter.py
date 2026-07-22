"""JSON metadata emitter for WorldView products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps WorldView's own extraction (the metadata
dict populated by ``product_worldview.Product_Worldview.extractMetadata``),
declares the WorldView mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output matches ``TDS/template/WV-template.json``
— structure and values. Unlike GeoEye-1/QuickBird-2, platformShortName and
instrumentShortName are supplied by the DYNAMIC layer: the WorldView mission
covers WV1/WV2/WV3/Legion, so platform identity varies per product. Which
layer fills a slot is the mission's choice — the generator merges uniformly.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from worldview_json import __version__

# WorldView mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": {
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
            "acquisitionParameters": {"wavelengths": {"spectralRange": "VIS"}},
        },
        "productInformation": {
            "resourceLineage": {"processStep": {
                "description": "EOPF-EOS Converter for WorldView",
                "reference": {"title": "EOPF-EOS Specialization for WorldView products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for WorldView",
                    "edition": __version__}},
            }},
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


def _operational_mode(met, product):
    """INFERRED native->spec operationalMode (spec Table 2 association is OCR-garbled).

    Mapping by band count, with a STEREO override when the native processed
    level denotes a stereo product. FLAGGED in worldview_fields.md.
    """
    processed = _gv(met, M.METADATA_PROCESSING_LEVEL) or ""
    if "Stereo" in processed:
        return "STEREO"
    nb = _gv(met, "numberOfBands")
    try:
        nb = int(float(nb))
    except (TypeError, ValueError):
        nb = None
    if nb == 1:
        return "PANCHROMATIC"
    if nb in (3, 4):
        return "MS4B"
    if nb == 8:
        return "MS8B"
    return None


def _processing_level(met):
    """INFERRED productInformation.processingLevel from the typecode level token.

    Spec enum (1B/2A/3) is OCR-suspect and reviewer-disputed. Only the
    unambiguous tokens are mapped; others are omitted. FLAGGED.
    """
    typecode = _gv(met, M.METADATA_TYPECODE) or ""
    level = typecode.split("_")[-1] if typecode else ""
    return {"2A": "2A", "MP": "3"}.get(level)


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

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": {
                "platform": {"platformShortName": _platform_short_name(met, is_legion)},
                "instrument": {"instrumentShortName":
                               INSTRUMENT_SHORTNAME.get(instrument_native, instrument_native)},
                "acquisitionParameters": {
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _operational_mode(met, product),
                    "resolution": float(resolution) if resolution is not None else None,
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": float(sun_az) if sun_az is not None else None,
                        "illuminationElevationAngle": float(sun_el) if sun_el is not None else None,
                    },
                },
            },
            "productInformation": {
                "size": int(size),
                "cloudCover": float(cloud) if cloud is not None else None,
                "productType": typecode,
                "processingLevel": _processing_level(met),
                "resourceLineage": {"processStep": {
                    "stepDateTime": {"created": created},
                    "source": {"citation": native_name, "processedLevel": _processed_level(met)},
                    "output": {"sourceCitation": {"title": "%s.ZIP" % eo_product_name}},
                }},
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
                              do_validate=do_validate)
