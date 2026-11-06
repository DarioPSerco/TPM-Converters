"""JSON metadata emitter for PLEIADES NEO products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps PNEO's own extraction (the metadata
dict populated by ``product_pneo.Product_Pneo.extractMetadata``), declares
the PLEIADES NEO mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
PLEIADES NEO PRODUCTS" 1.01 through its own placeholder template
(``feature_template_pln.json``) and matches ``TDS/template/PLN-template.json``.

Same Airbus-DIMAP family and same specialization layout as Pleiades
(``pleiades_json/json_emitter.py``); the PNEO differences are in
``product_pneo`` (product types, platforms, wavelength tables).

Spec readings encoded here:
- lineage: ONE process step, the EOPF-EOS converter. Its source follows
  Table 19 (``sourceCitation.title`` + ``processedLevel.code``), not the
  first example's ``citation``. processedLevel code and processingLevel
  (Table 18) are both ``L1A`` / ``L2`` / ``L3`` (the second example's
  ``1A`` is not one of Table 18's allowed values).
- processingDate: mandatory in Table 18 although the examples leave it out.
- cloudCover: mandatory (Table 20).
- the native product name is the delivery ZIP the conversion starts from,
  so the packager and the runner can find the native product again from
  the manifest.
- acquisitionParameters: one entry per component - one outside the bundle,
  MS then PAN for a bundle (the example's order). Orbit number / direction
  sit in each entry, as in the examples.
- wavelengths: one entry per row of Table 15 (Table 16 for a bundle),
  discreteWavelengths the mean of the row's range (Table 14).
- acquisitionAngles: every angle is optional and left out when the native
  product does not carry it (Table 13).
- links titles: Tables 22 / 23 (``Native EO Product`` / ``Preview Image``),
  not the example's ``Native File`` / ``Product browse``. Previews sit in
  ``/previews/overviews/`` (section 3.4): ``<EO name>.PNG``, or
  ``<EO name>_MS.PNG`` + ``<EO name>_PAN.PNG`` for a bundle.
- referenceSystemIdentifier (Table 17) only for a geo-referenced product
  (level L2 / L3).
- output sourceCitation: the package file name (``<EO name>.ZIP``), as in
  the bundle example.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from pneo_json import __version__
from pneo_json import product_pneo as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_pln.json"

# PLEIADES NEO mission-fixed values - template slots constant for this
# mission, shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"instrumentShortName": "PNEO", "sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for PLEIADES NEO",
                "reference": [{"title": "EOPF-EOS Specialization for PLEIADES NEO products",
                               "edition": "1.01"}],
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for PLEIADES NEO",
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
    return [{
        "beginningDateTime": c["begin"],
        "endingDateTime": c["end"] or c["begin"],
        "operationalMode": c["operationalMode"],
        "resolution": c["resolution"],
        "acquisitionType": "NOMINAL",
        "acquisitionAngles": dict(c["angles"]),
        "orbitNumber": c["orbitNumber"],
        "orbitDirection": c["orbitDirection"],
        "wavelengths": P.wavelengths(c["kind"], c["bundle"]),
    } for c in components]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """PLEIADES NEO per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    ring = _la(met, "footprintRing")
    components = _la(met, "components") or []
    measurements = _la(met, "measurements") or []
    size = _gv(met, M.METADATA_PRODUCT_SIZE)

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": [ring] if ring else None},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformShortName": _la(met, "platformShortName")},
                "acquisitionParameters": _acquisition_parameters(components) or None,
            }],
            "productInformation": {
                "size": int(size) if size is not None else None,
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
                "measurements": [{
                    "href": "/measurements/%s" % m["href"],
                    "type": m["type"],
                    "title": "Native EO Product",
                    "category": "DATA",
                } for m in measurements] or None,
                "previews": [{
                    "href": "/previews/overviews/%s%s.PNG" % (eo_product_name, c["previewSuffix"]),
                    "type": "image/png",
                    "title": "Preview Image",
                    "category": "OVERVIEW",
                } for c in components] or None,
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
