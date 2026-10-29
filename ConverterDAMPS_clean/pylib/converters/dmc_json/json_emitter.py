"""JSON metadata emitter for Beijing-1 / NigeriaSat-1 / UK-DMC-1 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps this mission's own extraction (the
metadata filled by ``product_dmc.Product_DMC.extractMetadata``), declares the
mission-fixed value map, and hands both layers to the mission-agnostic
generator. Output follows "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1
and UK-DMC-1 products" 1.0 through its own placeholder template
(``feature_template_dmc.json``) and matches ``TDS/template/DMC-template.json``.

Spec readings where the spec tables and its section
6.1 example differ:
- package name: the 10-character type code (Table 1 <TTTTTTTTTT>, e.g.
  ``L1_OPT_MS_``) then the '_' separator (``L1_OPT_MS__2017...``).
- sensing times and orbit fields sit flat in ``acquisitionParameters[0]``,
  not in nested temporalInformation / orbitParameters objects, as in the
  other mission converters.
- every datetime is YYYY-MM-DDThh:mm:ss.sssZ (Table 6).
- lineage per Table 17, as in the other mission converters: stepDateTime,
  reference, ``source[0].sourceCitation.title`` (the native .dim) +
  ``processedLevel.code``, ``output[0]`` = the package ZIP name.
- link titles from Tables 19 / 20: ``Native EO Product`` / ``Preview MS
  Image``.
- wavelengths per Table 14: one entry per spectral range, start / end its
  outer bounds, discreteWavelengths the band means.

Other readings:
- platformSerialIdentifier and cloudCover are written although the spec
  tables leave them out (they are in the section 6.1 example).
  platformSerialIdentifier comes from product_dmc.PLATFORMS.
- cloudCover, orbitNumber, orbitDirection, referenceSystemIdentifier and the
  along / across track incidence angles are written only when the native
  product carries them.
- measurements link: the DIMAP header <dataset>.dim (the entry file, an XML),
  media type ``application/xml``; the whole delivery is in measurements/.
- processingLevel ``"1"`` (Table 16), processedLevel ``L1R`` / ``L1T``
  (Table 17), operationalMode ``MS3B`` (Table 10).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from dmc_json import __version__
from dmc_json import product_dmc as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_dmc.json"

CONVERTER_NAME = "EOPF-EOS Converter for Beijing-1, Nigeriasat-1 and UK-DMC-1"
SPEC_TITLE = "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1 and UK-DMC-1 products"
SPEC_EDITION = "1.0"
MEASUREMENTS_MEDIA_TYPE = "application/xml"

# mission-fixed values - template slots constant for the three satellites,
# shaped as a partial tree mirroring the template
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"instrumentShortName": P.INSTRUMENT, "sensorType": "OPTICAL"},
            "acquisitionParameters": [{
                "acquisitionType": "NOMINAL",
                "wavelengths": P.wavelengths(),
            }],
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": CONVERTER_NAME,
                "reference": [{"title": SPEC_TITLE, "edition": SPEC_EDITION}],
                "processingInformation": {"softwareReference": {
                    "title": CONVERTER_NAME,
                    "edition": __version__}},
            }]}],
        },
        "links": {
            "measurements": [{"type": MEASUREMENTS_MEDIA_TYPE}],
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


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_layers(met, product, eo_product_name, native_product_name=None):
    """Per-product dynamic values, from this mission's extraction. A missing
    mandatory value leaves its template placeholder in place, so validation
    fails with the field path; a missing optional value leaves the key out."""
    native_name = (native_product_name
                   or getattr(product, "dim_name", None)
                   or eo_product_name)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    # spec Table 11: no ending time -> the beginning time
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    ring = _la(met, "footprintRing")
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": [ring] if ring else None},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {
                    "platformShortName": _gv(met, M.METADATA_PLATFORM),
                    "platformSerialIdentifier": _gv(met, M.METADATA_PLATFORM_ID),
                },
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "resolution": _float_or_none(_gv(met, M.METADATA_RESOLUTION)),
                    "orbitNumber": _int_or_none(_gv(met, M.METADATA_ORBIT)),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "acquisitionAngles": {
                        "illuminationAzimuthAngle": _float_or_none(_gv(met, M.METADATA_SUN_AZIMUTH)),
                        "illuminationElevationAngle": _float_or_none(_gv(met, M.METADATA_SUN_ELEVATION)),
                        "alongTrackIncidenceAngle": _float_or_none(
                            _gv(met, M.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE)),
                        "acrossTrackIncidenceAngle": _float_or_none(
                            _gv(met, M.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE)),
                    },
                }],
            }],
            "productInformation": {
                "size": int(size),
                "cloudCover": _float_or_none(_gv(met, M.METADATA_CLOUD_COVERAGE)),
                "productType": _gv(met, M.METADATA_TYPECODE),
                "referenceSystemIdentifier": _la(met, "referenceSystemIdentifier"),
                "processingLevel": _gv(met, M.METADATA_PROCESSING_LEVEL),
                "processingDate": _gv(met, M.METADATA_PROCESSING_TIME),
                "resourceLineage": [{"processStep": [{
                    "stepDateTime": {"created": created},
                    "source": [{
                        "sourceCitation": {"title": native_name},
                        "processedLevel": {"code": _gv(met, P.PROCESSED_LEVEL_CODE)},
                    }],
                    "output": [{"sourceCitation": {"title": "%s.ZIP" % eo_product_name}}],
                }]}],
            },
            "links": {
                "measurements": [{"href": "/measurements/%s" % native_name}],
                "previews": [{"href": "/previews/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
