"""JSON metadata emitter for RapidEye products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps RapidEye's own extraction (the metadata
dict populated by ``product_rapideye.Product_Rapideye.extractMetadata``),
declares the mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
RAPIDEYE PRODUCTS" 1.01 through its own placeholder template
(``feature_template_re.json``) and matches ``TDS/template/RE-template.json``.

Spec readings encoded here (the tables win over the example manifest):
- product type: ``L1BOPT_MS_`` (scope, Tables 1 and 17), not Table 2's
  ``L1B_OPT_MS``.
- status: ``ACQUIRED``; Table 5 misspells it ``AQUIRED``.
- lineage: ONE process step, the converter (Table 18), as for SkySat; the
  example adds a RapidEye processor step the tables do not describe.
- processedLevel code: ``L1B`` / ``L3`` (Table 18), not the example's ``L3A``.
- description and titles: ``Rapideye`` as Table 18 fixes them.
- reference edition: this document's issue, 1.01; Table 18's ``1.0`` is an
  example.
- acquisitionAngles: Table 13's keys. ``acrossTrackIncidenceAngle`` is the
  native spacecraft view angle, as for SkySat, and left out when absent;
  ``alongTrackIncidenceAngle`` has no native source; the example's
  ``incidenceAngle`` is not in the table.
- wavelengths: outer bounds of each range of Table 15, discreteWavelengths the
  band means (657.5 nm, the example rounds to 657). A 3-band product carries
  the VIS range only.
- links: titles from Tables 21/22 (the example says ``Native File`` and
  ``Product browse``); previews under ``/previews/overviews/`` (section 4).
- cloudCover (Table 19) and referenceSystemIdentifier (Table 16) are written
  only when the native product carries them.
- the native product name is the metadata file the conversion starts from
  (``<stem>_metadata.xml``), as for the other missions, so the packager and
  the runner can find the native product again from the manifest.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from rapideye_json import __version__
from rapideye_json import product_rapideye as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_re.json"

CONVERTER_NAME = "EOPF-EOS Converter for Rapideye"

# RapidEye mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"instrumentShortName": "REIS", "sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": CONVERTER_NAME,
                "reference": {"title": "EOPF-EOS Specialization for Rapideye products",
                              "edition": "1.01"},
                "processingInformation": {"softwareReference": {
                    "title": CONVERTER_NAME,
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


def _wavelengths(num_bands):
    """spec Table 15 rows of the band count."""
    ranges = P.WAVELENGTHS.get(num_bands)
    if ranges is None:
        return None
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands),
        "endWavelength": max(b[1] for b in bands),
        "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
    } for spectral_range, bands in ranges]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """RapidEye per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    level_code = _gv(met, P.PROCESSED_LEVEL_CODE)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
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
                "platform": {"platformShortName": _gv(met, P.PLATFORM_SHORT_NAME)},
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "resolution": _float_or_none(_gv(met, M.METADATA_RESOLUTION)),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "wavelengths": _wavelengths(product.num_bands),
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": _float_or_none(_gv(met, M.METADATA_SUN_AZIMUTH)),
                        "illuminationElevationAngle": _float_or_none(_gv(met, M.METADATA_SUN_ELEVATION)),
                        "acrossTrackIncidenceAngle": _la(met, "acrossTrackIncidenceAngle"),
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
                "previews": [{"href": "/previews/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
