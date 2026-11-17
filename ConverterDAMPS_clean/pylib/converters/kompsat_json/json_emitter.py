"""JSON metadata emitter for KOMPSAT-1 / KOMPSAT-2 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps KOMPSAT's own extraction (the metadata
dict populated by ``product_kompsat.Product_Kompsat.extractMetadata``),
declares the mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
KOMPSAT PRODUCTS" 1.0 through its own placeholder template
(``feature_template_ko.json``) and matches ``TDS/template/KO-template.json``.

Spec readings encoded here (the tables win over the example manifests):
- id / title: the package name WITHOUT extension (Table 3); the examples add
  ``.ZIP``.
- status: ``ACQUIRED`` (Table 5).
- acquisitionParameters: one entry per component - one for L1BORT_PAN, PAN
  then MS4B for a bundle (the L1_GEO_BDL example's two entries).
- resolution: Table 2 per satellite and mode (6.6 / 1 / 4 m); the examples'
  0.5 is a placeholder.
- wavelengths: the key of Table 14 and of the examples (Table 10 misspells
  it ``wavelenghts``); outer bounds of each range of Table 16 and the band
  means as discreteWavelengths.
- acquisitionAngles: Table 13 keys, each written when the native product
  carries it; the object is mandatory for KOMPSAT-1 (Table 10), so a
  KOMPSAT-1 product with no angle fails.
- orbitNumber / orbitDirection: in every acquisitionParameters entry (Table 12).
- processingLevel: ``1B`` for L1BORT_PAN, ``1`` for the bundles (Table 18);
  the L1BORT_PAN example says ``1``.
- processedLevel code: ``L1B`` / ``L1R`` / ``L1G`` (Table 19).
- referenceSystemIdentifier: always the EPSG:4326 URI (Table 17, fixed value).
- lineage: ONE process step, the converter (Table 19). Its source follows
  Table 19 (``sourceCitation.title``), not the examples' ``citation``; the
  output citation is the package name with ``.ZIP`` (Table 19 example).
- links titles: Tables 22 / 23 (the examples say ``Native File`` /
  ``Product browse``); previews under ``/previews/overviews/`` (section 4).
- cloudCover (Table 20) only when the native product carries it.
- no platformSerialIdentifier: Table 8 does not list it.
- the native product name is the AUX metadata file the conversion starts
  from, as for the other missions, so the packager and the runner can find
  the native product again from the manifest.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from kompsat_json import __version__
from kompsat_json import product_kompsat as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_ko.json"

CONVERTER_NAME = "EOPF-EOS Converter for KOMPSAT"

# KOMPSAT mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "referenceSystemIdentifier": P.REFERENCE_SYSTEM,
            "resourceLineage": [{"processStep": [{
                "description": CONVERTER_NAME,
                "reference": [{"title": "EOPF-EOS Specialization for KOMPSAT products",
                               "edition": "1.0"}],
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


def _acquisition_parameters(components):
    params = []
    for c in components:
        par = {
            "beginningDateTime": c["begin"],
            "endingDateTime": c["end"] or c["begin"],
            "acquisitionType": "NOMINAL",
            "operationalMode": c["mode"],
            "resolution": c["resolution"],
            "orbitDirection": c["orbitDirection"],
            "orbitNumber": c["orbitNumber"],
        }
        if c["angles"]:
            par["acquisitionAngles"] = dict(c["angles"])
        par["wavelengths"] = c["wavelengths"]
        params.append(par)
    return params


def build_layers(met, product, eo_product_name, native_product_name=None):
    """KOMPSAT per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    ring = _la(met, "footprintRing")
    image = _la(met, "nativeDataFile")
    components = _la(met, "components") or []
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
                "instrument": {"instrumentShortName": _gv(met, P.INSTRUMENT_SHORT_NAME)},
                "acquisitionParameters": _acquisition_parameters(components) or None,
            }],
            "productInformation": {
                "size": int(size),
                "cloudCover": _float_or_none(_gv(met, M.METADATA_CLOUD_COVERAGE)),
                "productType": _gv(met, M.METADATA_TYPECODE),
                "processingDate": _gv(met, M.METADATA_PROCESSING_TIME),
                "processingLevel": _gv(met, M.METADATA_PROCESSING_LEVEL),
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
