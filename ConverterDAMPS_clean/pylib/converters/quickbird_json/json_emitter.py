"""JSON metadata emitter for QuickBird-2 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps QuickBird-2's own extraction (the
metadata dict populated by ``product_quickbird.Product_Quickbird.
extractMetadata``), declares the QuickBird-2 mission-fixed value map, and
hands both layers to the mission-agnostic generator. Output matches
``TDS/template/QB2-template.json`` — structure and values. A future mission
plugs in the same way: its own MISSION_VALUES + its own dynamic layer, no
change to the common core.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from quickbird_json import __version__

# QuickBird-2 mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": {
            "platform": {"platformShortName": "QuickBird-2", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "BGI", "sensorType": "OPTICAL"},
            "acquisitionParameters": {"wavelengths": {"spectralRange": "VIS"}},
        },
        "productInformation": {
            "resourceLineage": {"processStep": {
                "description": "EOPF-EOS Converter for QuickBird-2",
                "reference": {"title": "EOPF-EOS Specialization for QuickBird-2 products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for QuickBird-2",
                    "edition": __version__}},
            }},
        },
    },
}


def _gv(met, key):
    v = met.getMetadataValue(key)
    if not met.valueExists(v):
        return None
    return v


def _norm_dt(s):
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
    toks = [t for t in str(footprint).split() if t != ""]
    ring = []
    for i in range(0, len(toks) - 1, 2):
        ring.append([float(toks[i + 1]), float(toks[i])])  # [lon, lat]
    return [ring]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """QuickBird-2 per-product dynamic values, from this mission's extraction."""
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
    processed = (_gv(met, M.METADATA_PROCESSING_LEVEL) or "").replace("other: ", "").strip() or None
    level_token = typecode.split("_")[-1] if typecode else None
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": {"acquisitionParameters": {
                "beginningDateTime": begin,
                "endingDateTime": end,
                "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                "resolution": float(resolution) if resolution is not None else None,
                "acquisitionAngles": {
                    "illuminationAzimuthAngle": float(sun_az) if sun_az is not None else None,
                    "illuminationElevationAngle": float(sun_el) if sun_el is not None else None,
                },
            }},
            "productInformation": {
                "size": int(size),
                "cloudCover": float(cloud) if cloud is not None else None,
                "productType": typecode,
                "processingLevel": level_token,
                "resourceLineage": {"processStep": {
                    "stepDateTime": {"created": created},
                    "source": {"citation": native_name, "processedLevel": processed},
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
