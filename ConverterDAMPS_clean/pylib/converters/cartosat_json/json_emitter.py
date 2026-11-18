"""JSON metadata emitter for IRS-P5 (Cartosat-1) and IRS-P6 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps this mission's own extraction (the
metadata filled by ``product_cartosat.Product_Cartosat.extractMetadata``),
declares the mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS Specialization for
IRS-P5 (Cartosat-1) products" 1.0, applied to IRS-P6 products as well,
through its own placeholder template (``feature_template_ir5.json``) and
matches ``TDS/template/IR5-template.json``.

Spec readings encoded here (the tables win over the section 6.1 example):
- id / title: the package name without extension (section 5.2, Table 6).
- status: ``ACQUIRED`` (Table 5 spells it ``AQUIRED``).
- every datetime is YYYY-MM-DDThh:mm:ss.sssZ (Tables 6, 11, 16).
- acquisitionParameters: one entry per orthoimage of the delivery (one for a
  DSM tile and an IRS-P6 orthoimage); sensing times and orbit fields sit
  flat in each entry, as in the example, not in nested temporalInformation /
  orbitParameters objects.
- operationalMode: the Table 2 association with the product type, ``PAN``
  for L3_ORT_PAN and ``STER`` for L3_DSM____ (Table 10 lists only ``PAN``).
- resolution: Table 10 fixed value 2.5 for IRS-P5; 20 (the LISS-III
  orthoimage pixel size) for IRS-P6.
- wavelengths: the key of Table 14 and of the example (Table 10 spells it
  ``wavelenghts``); one entry per spectral range, start / end its outer
  bounds, discreteWavelengths the band means, all numbers (Table 14 writes
  the fixed values as strings; the example's 625E-09 is not the band mean).
  IRS-P5: VNIR 500-850 nm; IRS-P6: VIS, NIR and SWIR LISS-III bands.
- acquisitionAngles: the two illumination angles (Table 13, mandatory for
  L3_ORT_PAN, Table 10); no incidence angle (optional, the native tilt
  angle does not say along or across track); none for a DSM tile.
- orbitNumber / orbitDirection: in every acquisitionParameters entry
  (Table 12).
- processingLevel ``3`` and processingDate (Table 16, mandatory although
  the example leaves them out); processedLevel code ``L3`` (Table 17).
- referenceSystemIdentifier: the EPSG URI of the native CRS (Table 15 asks
  for a code space pointing to the CRS; ``urn:esa:eop:crs`` is the cfg
  code space).
- lineage: one process step, the converter (Table 17). Its description is
  the Table 17 fixed value ``EOPF-EOS Converter for IRS-P5``, with IRS-P6
  for an IRS-P6 product. Its source follows
  Table 17 (``sourceCitation.title``), not the example's ``citation``; the
  output citation is the package name with ``.ZIP``.
- links titles: Tables 19 / 20 (the example says ``Native File`` /
  ``Product browse``); measurements type ``image/tiff`` (GeoTIFF natives) or
  ``application/xml`` (IRS-P6, the link being its metadata.xml); previews
  under ``/previews/overviews/`` (section 4).
- the native product name is the lineage citation of the product (the entry
  file, with its folder for IRS-P6), so the packager and the runner can find
  the native product again from the manifest.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from cartosat_json import __version__
from cartosat_json import product_cartosat as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_ir5.json"

CONVERTER_NAME = "EOPF-EOS Converter for IRS-P5 and IRS-P6"
# lineage description per platformShortName (Table 17 fixed value for IRS-P5)
DESCRIPTION = "EOPF-EOS Converter for %s"
SPEC_TITLE = "EOPF-EOS Specialization for IRS-P5 (Cartosat-1) products"
SPEC_EDITION = "1.0"

# mission-fixed values - template slots constant for both platforms, shaped
# as a partial tree mirroring the template
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "reference": [{"title": SPEC_TITLE, "edition": SPEC_EDITION}],
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


def _acquisition_parameters(components):
    """acquisitionParameters entries, keys in the section 6.1 example order."""
    params = []
    for c in components:
        par = {
            "beginningDateTime": c["begin"],
            "endingDateTime": c["end"] or c["begin"],
            "operationalMode": c["mode"],
            "resolution": c["resolution"],
            "acquisitionType": "NOMINAL",
            "orbitNumber": c["orbitNumber"],
            "orbitDirection": c["orbitDirection"],
            "wavelengths": c["wavelengths"],
        }
        if c["angles"]:
            par["acquisitionAngles"] = dict(c["angles"])
        params.append(par)
    return params


def build_layers(met, product, eo_product_name, native_product_name=None):
    """Per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "nativeFileName", None)
                   or eo_product_name)
    created = _gv(met, P.CREATION_TIME)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin
    ring = _la(met, "footprintRing")
    data_file = _la(met, "nativeDataFile")
    components = _la(met, "components") or []
    size = getattr(product, "tmpSize", 0) or 0
    platform = _gv(met, P.PLATFORM_SHORT_NAME)

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": [ring] if ring else None},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformShortName": platform},
                "instrument": {"instrumentShortName": _gv(met, P.INSTRUMENT_SHORT_NAME)},
                "acquisitionParameters": _acquisition_parameters(components) or None,
            }],
            "productInformation": {
                "size": int(size),
                "productType": _gv(met, M.METADATA_TYPECODE),
                "referenceSystemIdentifier": _la(met, "referenceSystemIdentifier"),
                "processingLevel": _gv(met, M.METADATA_PROCESSING_LEVEL),
                "processingDate": _gv(met, M.METADATA_PROCESSING_TIME),
                "resourceLineage": [{"processStep": [{
                    "description": DESCRIPTION % platform if platform else None,
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
                    "href": "/measurements/%s" % data_file if data_file else None,
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
