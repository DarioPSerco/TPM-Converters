"""JSON metadata emitter for PLEIADES products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps Pleiades' own extraction (the metadata
dict populated by ``product_pleiades.Product_Pleiades.extractMetadata``),
declares the PLEIADES mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output matches ``TDS/template/PL1-template.json``
— structure and values.

The Pleiades/PNEO (Airbus DIMAP) template family differs from the shared
optical one: it drops resolution/wavelengths/cloudCover/processingLevel and
adds bbox, platformSerialIdentifier, orbit fields, WRS grids and across/along
track incidence angles. The overlay can add keys but never remove them, so
this mission uses its own placeholder template
(``feature_template_pl1.json``) through the generator's existing
``template_path`` extension point — no change to the common core.

Optional angles may carry the pipeline's -999999 sentinel: they are treated
as missing (pruned), so the template placeholder survives and validation
fails loudly instead of shipping -999999 in delivered metadata.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from pleiades_json import __version__

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_pl1.json"

NO_NUMERIC_VALUE = -999999.0

# PLEIADES mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": {
            "platform": {"platformShortName": "PLEIADES", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "HiRI", "sensorType": "OPTICAL"},
        },
        "productInformation": {
            "resourceLineage": {"processStep": {
                "description": "EOPF-EOS Converter for PLEIADES",
                "reference": {"title": "EOPF-EOS Specialization for PLEIADES products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for PLEIADES",
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


def _num(v):
    if v is None:
        return None
    f = float(v)
    if f == NO_NUMERIC_VALUE:
        return None
    return f


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


def _bbox(coordinates):
    ring = coordinates[0]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return [min(lons), min(lats), max(lons), max(lats)]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """PLEIADES per-product dynamic values, from this mission's extraction."""
    native_name = native_product_name or getattr(product, "origName", None) or eo_product_name
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _norm_dt(_gv(met, M.METADATA_PROCESSING_TIME))
    start_date = _gv(met, M.METADATA_START_DATE)
    start_time = _gv(met, M.METADATA_START_TIME)
    begin = _norm_dt("%sT%s" % (start_date, start_time)) if start_date and start_time else None
    end = begin  # single-acquisition mission: stop == start (refineMetadata)

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None
    bbox = _bbox(coordinates) if coordinates else None

    orbit = _gv(met, M.METADATA_ORBIT)
    serial = _gv(met, M.METADATA_PLATFORM_ID)
    sun_az = _num(_gv(met, M.METADATA_SUN_AZIMUTH))
    sun_el = _num(_gv(met, M.METADATA_SUN_ELEVATION))
    across = _num(_gv(met, M.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE))
    along = _num(_gv(met, M.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE))
    processed = _gv(met, M.METADATA_PROCESSING_LEVEL)
    size = _gv(met, M.METADATA_PRODUCT_SIZE)

    dynamic = {
        "id": eo_product_name,
        "bbox": bbox,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": {
                "platform": {"platformSerialIdentifier": str(serial) if serial is not None else None},
                "acquisitionParameters": {
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "orbitNumber": int(orbit) if orbit is not None else None,
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "wrsLongitudeGrid": _gv(met, M.METADATA_WRS_LONGITUDE_GRID_NORMALISED),
                    "wrsLatitudeGrid": _gv(met, M.METADATA_WRS_LATITUDE_GRID_NORMALISED),
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": sun_az,
                        "illuminationElevationAngle": sun_el,
                        "acrossTrackIncidenceAngle": across,
                        "alongTrackIncidenceAngle": along,
                    },
                },
            },
            "productInformation": {
                "size": int(size) if size is not None else None,
                "productType": typecode,
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
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
