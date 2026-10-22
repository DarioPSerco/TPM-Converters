"""JSON metadata emitter for PLEIADES products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps Pleiades' own extraction (the metadata
dict populated by ``product_pleiades.Product_Pleiades.extractMetadata``),
declares the PLEIADES mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
PLEIADES PRODUCTS" 1.01 through its own placeholder template
(``feature_template_pl1.json``) and matches ``TDS/template/PL1-template.json``.

Spec readings encoded here:
- lineage: ONE process step, the EOPF-EOS converter. Its source follows
  Table 19 (``sourceCitation.title`` + ``processedLevel.code``); the
  example leaves processedLevel out. processedLevel code ``L1A`` / ``L2`` /
  ``L3``, processingLevel (Table 18) ``1A`` / ``2`` / ``3``.
- processingDate: mandatory in Table 18 although the examples leave it out.
- the native product name is the delivery ZIP the conversion starts from,
  so the packager and the runner can find the native product again from
  the manifest.
- acquisitionParameters: one entry per component - one outside the bundle,
  MS then PAN for a bundle (the example's order). Orbit number / direction
  sit in each entry, as in the examples.
- wavelengths: one entry per spectral range of Tables 15 / 16, start / end
  the outer bounds of its bands, discreteWavelengths the band centres.
- acquisitionAngles: every angle is optional and left out when the native
  product does not carry it (Table 13).
- links titles: Tables 21 / 22 (``Native EO Product`` / ``Preview Image``),
  not the example's ``Native File`` / ``Product browse``. Previews sit in
  ``/previews/overviews/`` (section 4): ``<EO name>.PNG``, or
  ``<EO name>_MS.PNG`` + ``<EO name>_PAN.PNG`` for a bundle.
- referenceSystemIdentifier (Table 17) only for a geo-referenced product
  (level 2 / 3).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from pleiades_json import __version__
from pleiades_json import product_pleiades as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_pl1.json"

# PLEIADES mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"instrumentShortName": "HiRI", "sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for PLEIADES",
                "reference": [{"title": "EOPF-EOS Specialization for PLEIADES products",
                               "edition": "1.01"}],
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for PLEIADES",
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
        "wavelengths": P.wavelengths(c["kind"]),
    } for c in components]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """PLEIADES per-product dynamic values, from this mission's extraction."""
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
