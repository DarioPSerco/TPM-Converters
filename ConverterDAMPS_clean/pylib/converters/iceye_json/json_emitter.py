"""JSON metadata emitter for ICEYE products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps ICEYE's own extraction (the metadata
dict populated by ``product_iceye.Product_Iceye.extractMetadata``), declares
the ICEYE mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output matches ``TDS/template/ICE-template.json``
— structure and values.

ICEYE is SAR: its template carries fields the optical missions don't
(orbitNumber, orbitDirection, polarisation, antennaLookDirection,
incidenceAngle) and lacks the optical ones (spectralRange, cloudCover,
processingLevel, illumination angles). The overlay can add keys but never
remove them, so this mission uses its own placeholder template
(``feature_template_sar.json``) through the generator's existing
``template_path`` extension point — no change to the common core.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from iceye_json import __version__

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_sar.json"

# ICEYE mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": {
            "platform": {"platformShortName": "ICEYE", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "SAR", "sensorType": "RADAR"},
        },
        "productInformation": {
            "resourceLineage": {"processStep": {
                "description": "EOPF-EOS Converter for ICEYE",
                "reference": {"title": "EOPF-EOS Specialization for ICEYE products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for ICEYE",
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
    """ICEYE per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "productFolderName", None)
                   or eo_product_name)
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE)
                       or _gv(met, M.METADATA_PROCESSING_TIME))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

    orbit = _gv(met, M.METADATA_ORBIT)
    incidence = _gv(met, M.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
    # azimuth resolution local attribute set by refineMetadata (the old XML
    # METADATA_RESOLUTION slot is never filled by this mission's extraction)
    resolution = met.getLocalAttributeValue("azimuthResolution")
    serial = _gv(met, M.METADATA_SATELLITE)
    processed = _gv(met, "level")
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
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
                    "orbitNumber": str(orbit) if orbit is not None else None,
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "wrsLongitudeGrid": _gv(met, M.METADATA_WRS_LONGITUDE_GRID_NORMALISED),
                    "wrsLatitudeGrid": _gv(met, M.METADATA_WRS_LATITUDE_GRID_NORMALISED),
                    "polarisationMode": _gv(met, M.METADATA_POLARISATION_MODE),
                    "polarisationChannel": _gv(met, M.METADATA_POLARISATION_CHANNELS),
                    "antennaLookDirection": _gv(met, M.METADATA_ANTENNA_LOOK_DIRECTION),
                    "resolution": float(resolution) if resolution is not None else None,
                    "acquisitionAngles": {
                        "incidenceAngle": float(incidence) if incidence is not None else None,
                    },
                },
            },
            "productInformation": {
                "size": int(size),
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
