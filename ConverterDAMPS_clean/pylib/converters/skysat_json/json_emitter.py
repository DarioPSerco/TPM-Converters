"""JSON metadata emitter for SkySat products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps SkySat's own extraction (the metadata
dict populated by ``product_skysat.Product_Skysat.extractMetadata``),
declares the mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
SKYSAT PRODUCTS" 1.01 through its own placeholder template
(``feature_template_ssc.json``) and matches ``TDS/template/SSC-template.json``.

Spec readings encoded here:
- lineage: ONE process step, the EOPF-EOS converter (Table 19). Its source
  follows Table 19 (``sourceCitation.title`` + ``processedLevel.code``), not
  the example's ``citation``; ``common.json_template.lineage_citation``
  reads both.
- the native product name is the item metadata file the conversion starts
  from (``<item id>_metadata.json``), as for PlanetScope, so the packager and
  the runner can find the native item again from the manifest.
- processedLevel code (Table 19): ``L1A`` / ``L1B`` / ``L3B``, ``SYN`` for the
  SkySat Collect bundle. processingLevel (Table 18): ``1A`` / ``1B`` / ``3``,
  not the example's ``1``.
- processingDate: mandatory in Table 18 although the examples leave it out.
- acquisitionParameters: one entry per component - one outside the bundle,
  one per image kind of the SYNORT_BDL bundle, in the example's order
  (3-band pansharpened, 4-band pansharpened, 4-band analytic, panchromatic).
- wavelengths: ``endWavelength`` as Table 14 and the examples spell it; one
  entry per spectral range, start / end the outer bounds of its bands,
  discreteWavelengths the band centres (the example's VIS entry:
  450-695 nm, 482.5 / 555 / 650 nm).
- acquisitionAngles: acrossTrackIncidenceAngle from the item view angle;
  the optional alongTrackIncidenceAngle is left out (not delivered).
- links titles: Tables 22 / 23 (``Native EO Product`` / ``Preview Image``),
  not the example's ``Native File`` / ``Product browse``. Previews sit in
  ``/previews/overviews/`` (section 4) and keep the ``.PNG`` extension the
  text asks for, also for the four bundle overviews.
- cloudCover (Table 20, optional) and referenceSystemIdentifier (Table 17,
  geo-referenced products only) are written only when available.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from skysat_json import __version__
from skysat_json import product_skysat as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_ssc.json"

# SkySat mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"platformShortName": "SkySat", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "SkySat Camera", "sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for SkySat",
                "reference": [{"title": "EOPF-EOS Specialization for SkySat products",
                               "edition": "1.01"}],
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for SkySat",
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


def _acquisition_parameters(met, components, begin, end):
    angles = {
        "illuminationAzimuthAngle": _float_or_none(_gv(met, M.METADATA_SUN_AZIMUTH)),
        "illuminationElevationAngle": _float_or_none(_gv(met, M.METADATA_SUN_ELEVATION)),
        "acrossTrackIncidenceAngle": _float_or_none(_gv(met, M.METADATA_INSTRUMENT_INCIDENCE_ANGLE)),
    }
    resolution = _float_or_none(_gv(met, M.METADATA_RESOLUTION))
    return [{
        "beginningDateTime": begin,
        "endingDateTime": end,
        "operationalMode": c["operationalMode"],
        "resolution": resolution,
        "acquisitionType": "NOMINAL",
        "acquisitionAngles": dict(angles),
        "wavelengths": P.wavelengths(c["spectralRanges"]),
    } for c in components]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """SkySat per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    level_code = _gv(met, P.PROCESSED_LEVEL_CODE)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    ring = _la(met, "footprintRing")
    components = _la(met, "components") or []
    measurements = _la(met, "measurements") or []
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": [ring] if ring else None},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "acquisitionParameters": _acquisition_parameters(met, components, begin, end) or None,
            }],
            "productInformation": {
                "size": int(size),
                "referenceSystemIdentifier": _la(met, "referenceSystemIdentifier"),
                "cloudCover": _float_or_none(_gv(met, M.METADATA_CLOUD_COVERAGE)),
                "processingLevel": _gv(met, M.METADATA_PROCESSING_LEVEL),
                "productType": _gv(met, M.METADATA_TYPECODE),
                "processingDate": _gv(met, M.METADATA_PROCESSING_TIME),
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
