"""JSON metadata emitter for PlanetScope products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps PlanetScope's own extraction (the
metadata dict populated by
``product_planetscope.Product_Planetscope.extractMetadata``), declares the
mission-fixed value map, and hands both layers to the mission-agnostic
generator. Output follows "EOPF-EOS SPECIALIZATION FOR PLANETSCOPE PRODUCTS"
1.0 through its own placeholder template (``feature_template_psc.json``) and
matches ``TDS/template/PSC-template.json``.

Spec readings encoded here:
- lineage: TWO process steps (Table 18). Step 0 is the Planet processor
  (no sourceCitation in its source, the native product name in its output),
  step 1 the EOPF-EOS converter.
- wavelengths: the example spells the block ``wavelenghts``, Table 13
  ``wavelengths``; the plural is used, as for COSMO-SkyMed and WorldView.
  Table 13 names the upper bound ``stopWavelengthendWavelength`` (an edit
  left-over of stop/end); ``stopWavelength`` is used, as for the other
  missions. One entry per spectralRange of Table 14: start/stop are the
  outer bounds of the range, discreteWavelengths the band centres.
- orbitDirection: Table 12 spells ``OrbitDirection``; the example's
  ``orbitDirection`` is used, the camelCase every other key follows.
- processedLevel code: Table 18 (``L1A`` / ``L1B`` / ``L3B``, ``L3A`` for an
  ortho tile), in both steps; not the example's ``3``.
- cloudCover (Table 19, optional) and referenceSystemIdentifier (Table 16,
  mandatory if present) are written only when the native product carries
  them.
- the native product name is the item metadata file the conversion starts
  from (``<item id>_metadata.json``), as for the other missions, so the
  packager and the runner can find the native item again from the manifest.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from planetscope_json import __version__
from planetscope_json import product_planetscope as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_psc.json"

# PlanetScope mission-fixed values - template slots constant for this
# mission, shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{}, {
                "description": "EOPF-EOS Converter for PlanetScope",
                "reference": {"title": "EOPF-EOS Specialization for PlanetScope products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for PlanetScope",
                    "edition": __version__}},
            }]}],
        },
    },
}


def _gv(met, key):
    v = met.getMetadataValue(key)
    if not met.valueExists(v):
        return None
    return v


def _la(met, key):
    return met.getLocalAttributeValue(key)


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _wavelengths(mode):
    """spec Table 14 rows of the operational mode."""
    ranges = P.WAVELENGTHS.get(mode)
    if ranges is None:
        return None
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands),
        "stopWavelength": max(b[1] for b in bands),
        "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
    } for spectral_range, bands in ranges]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """PlanetScope per-product dynamic values, from this mission's
    extraction."""
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    level_code = _gv(met, P.PROCESSED_LEVEL_CODE)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    mode = _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE)
    instrument = _gv(met, P.INSTRUMENT_ID)
    ring = _la(met, "footprintRing")
    image = _la(met, "nativeDataFile")
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": [ring] if ring else None},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformShortName": P.PLATFORM_MAP.get(str(instrument))},
                "instrument": {"instrumentShortName": instrument},
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": mode,
                    "resolution": _float_or_none(_gv(met, M.METADATA_RESOLUTION)),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "wavelengths": _wavelengths(mode),
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": _float_or_none(_gv(met, M.METADATA_SUN_AZIMUTH)),
                        "illuminationElevationAngle": _float_or_none(_gv(met, M.METADATA_SUN_ELEVATION)),
                        "incidenceAngle": _float_or_none(_gv(met, M.METADATA_INSTRUMENT_INCIDENCE_ANGLE)),
                    },
                }],
            }],
            "productInformation": {
                "size": int(size),
                "cloudCover": _float_or_none(_gv(met, M.METADATA_CLOUD_COVERAGE)),
                "productType": _gv(met, M.METADATA_TYPECODE),
                "referenceSystemIdentifier": _la(met, "referenceSystemIdentifier"),
                "processingDate": _gv(met, M.METADATA_PROCESSING_TIME),
                "processingLevel": _gv(met, M.METADATA_PROCESSING_LEVEL),
                "resourceLineage": [{"processStep": [{
                    "source": [{"processedLevel": {"code": level_code}}],
                    "processingInformation": {"softwareReference": {
                        "title": _gv(met, P.PROCESSOR_NAME),
                        "edition": _gv(met, P.PROCESSOR_VERSION)}},
                    "output": [{"sourceCitation": {"title": native_name}}],
                }, {
                    "stepDateTime": {"created": created},
                    "source": [{
                        "sourceCitation": {"title": native_name},
                        "processedLevel": {"code": level_code},
                    }],
                    "output": [{"sourceCitation": {"title": "%s.ZIP" % eo_product_name}}],
                }]}],
            },
            "links": {
                "measurements": [{
                    "href": "/measurements/%s" % image if image else None,
                    "type": _la(met, "measurementsMediaType"),
                }],
                "preview": [{"href": "/preview/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
