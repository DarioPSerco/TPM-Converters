"""JSON metadata emitter for GEOSAT products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps GEOSAT's own extraction (the metadata
dict populated by ``product_geosat.Product_Geosat.extractMetadata``),
declares the GEOSAT mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
GEOSAT PRODUCTS" 1.01 through its own placeholder template
(``feature_template_geosat.json``) and matches
``TDS/template/GEOSAT-template.json``.

Spec readings encoded here (tables over examples, as for PNEO):
- lineage: ONE process step, described "GEOSAT processor" (Table 20). Its
  source follows Table 20 (``sourceCitation.title`` + ``processedLevel.code``),
  not the examples' ``citation``. processingLevel (Table 19) and
  processedLevel code are values of the allowed list (L1 / L2 / L1B / L1C /
  L1D / L2T / SYN); the examples' ``1`` / ``1B`` are not.
- the spec document goes in ``reference`` and the converter in
  ``processingInformation.softwareReference``, as in the examples (Table 20
  puts both under ``softwareReference``).
- output sourceCitation: the package name without extension (Table 20 and
  both examples).
- processingDate: mandatory in Table 19 although the examples leave it out.
- cloudCover (Table 21) and the acquisition angles (Table 13) are optional:
  left out when the native product does not carry them. orbitDirection
  likewise for GEOSAT-1 (Table 14: mandatory for GEOSAT-2 only).
- acquisitionParameters: one entry per component - one outside bundles and
  stereo pairs, MS then PAN for a bundle (the example's two entries), one
  per view for a stereo pair.
- links titles: Tables 23 / 24 (``Native EO Product`` / ``Preview Image``),
  not the examples' ``Native File`` / ``Product browse``. Previews sit in
  ``/previews/overviews/`` (section 4): ``<EO name>.PNG``, or one per
  component with a ``_MS`` / ``_PAN`` (bundle), ``_1`` / ``_2`` (stereo)
  suffix.
- referenceSystemIdentifier (Table 18) whenever the native product carries
  a CRS (mandatory, and checked, for the orthorectified levels).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from geosat_json import __version__
from geosat_json import product_geosat as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_geosat.json"

# GEOSAT mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "GEOSAT processor",
                "reference": [{"title": "EOPF-EOS Specialization for GEOSAT products",
                               "edition": "1.01"}],
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for GEOSAT",
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
            "operationalMode": c["operationalMode"],
            "resolution": c["resolution"],
            "acquisitionType": "NOMINAL",
            "orbitNumber": c["orbitNumber"],
        }
        if c["orbitDirection"]:
            par["orbitDirection"] = c["orbitDirection"]
        if c["angles"]:
            par["acquisitionAngles"] = dict(c["angles"])
        par["wavelengths"] = P.wavelengths(c["kind"])
        params.append(par)
    return params


def build_layers(met, product, eo_product_name, native_product_name=None):
    """GEOSAT per-product dynamic values, from this mission's extraction."""
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
                "instrument": {"instrumentShortName": _la(met, "instrumentShortName")},
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
                    "output": [{"sourceCitation": {"title": eo_product_name}}],
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
