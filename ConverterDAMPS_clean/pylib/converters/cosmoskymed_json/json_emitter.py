"""JSON metadata emitter for COSMO-SkyMed products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps COSMO-SkyMed's own extraction (the
metadata dict populated by
``product_cosmoskymed.Product_CosmoSkymed.extractMetadata``), declares the
mission-fixed value map, and hands both layers to the mission-agnostic
generator. Output matches ``TDS/template/CSK-template.json`` - structure and
values.

COSMO-SkyMed is SAR, and its manifest follows "EOPF-EOS SPECIALIZATION FOR
COSMO-SKYMED PRODUCTS": versus ICEYE it adds rangeResolution,
azimuthResolution, resolution, the wavelengths block, processingLevel and the
lineage processedLevel code, and it drops the WRS grids, the platform serial
identifier and antennaLookDirection. It therefore uses its own placeholder
template (``feature_template_csk.json``) through the generator's existing
``template_path`` extension point - no change to the common core.

Two spec readings are encoded here:
- wavelengths: the spec spells the block ``wavelength`` in Table 10 and
  ``wavelengths`` in the table that defines its content; the plural is used,
  under ``acquisitionParameters[0]``.
- lineage source: Table 16 is normative (``source[0].sourceCitation.title`` +
  ``source[0].processedLevel.code``), not the spec's own example, which nests
  processedLevel inside sourceCitation.

productType is one of the ten codes the spec allows (L1ASMU_SCS, L1ASMB_SCS,
L1BSM__DGM, L1CSM__GEC, L1DSM__GTC, L1ASCU_SCS, L1ASCB_SCS, L1BSC__DGM,
L1CSC__GEC, L1DSC__GTC), built by ``product_cosmoskymed.TYPECODE_MAP``.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from cosmoskymed_json import __version__
from cosmoskymed_json import product_cosmoskymed as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_csk.json"

# spec Table 14: the X-band SAR-2000 / CSG-SAR wavelength bounds are fixed
SPECTRAL_RANGE = "X-Band"
START_WAVELENGTH = 0.028
STOP_WAVELENGTH = 0.052

# COSMO-SkyMed mission-fixed values - template slots constant for this
# mission, shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "RADAR"},
            "acquisitionParameters": [{
                "wavelengths": [{
                    "spectralRange": SPECTRAL_RANGE,
                    "startWavelength": START_WAVELENGTH,
                    "stopWavelength": STOP_WAVELENGTH,
                }],
            }],
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for COSMO-SkyMed",
                "reference": {"title": "EOPF-EOS Specialization for COSMO-SkyMed products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for COSMO-SkyMed",
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


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _polygon_coordinates(footprint):
    """'lat lon lat lon ...' -> [[[lon, lat], ...]]"""
    toks = [t for t in str(footprint).split() if t != ""]
    ring = []
    for i in range(0, len(toks) - 1, 2):
        ring.append([float(toks[i + 1]), float(toks[i])])  # [lon, lat]
    return [ring]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """COSMO-SkyMed per-product dynamic values, from this mission's
    extraction."""
    # lineage citation: the native product file as delivered (the .h5, or the
    # .tgz of a GeoTIFF delivery). measurements link: the image file as it
    # lands in measurements/ - the same .h5, or the GeoTIFF out of the .tgz.
    native_name = (native_product_name
                   or _la(met, "nativeDataFile")
                   or getattr(product, "origName", None)
                   or eo_product_name)
    measurement_file = _la(met, "nativeDataFile") or native_name
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _gv(met, M.METADATA_DATASET_PRODUCTION_DATE)
    processed = _gv(met, M.METADATA_PROCESSING_TIME) or created
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

    satellite = _gv(met, P.SATELLITE_ID)
    mission = _gv(met, P.MISSION_ID)
    platform_short_name = P.SATELLITE_MAP.get(str(satellite)) if satellite else None
    instrument_short_name = P.INSTRUMENT_MAP.get(str(mission)) if mission else None

    incidence = _float_or_none(_gv(met, M.METADATA_INSTRUMENT_INCIDENCE_ANGLE))
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformShortName": platform_short_name},
                "instrument": {"instrumentShortName": instrument_short_name},
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "rangeResolution": _float_or_none(_la(met, "rangeResolution")),
                    "azimuthResolution": _float_or_none(_la(met, "azimuthResolution")),
                    "resolution": _float_or_none(_la(met, "resolution")),
                    "wavelengths": [{
                        "discreteWavelength": _float_or_none(_la(met, "radarWavelength")),
                    }],
                    "polarisationMode": _gv(met, M.METADATA_POLARISATION_MODE),
                    "polarisationChannel": _gv(met, M.METADATA_POLARISATION_CHANNELS),
                    "orbitNumber": _int_or_none(_gv(met, M.METADATA_ORBIT)),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "acquisitionAngles": {"incidenceAngle": incidence},
                }],
            }],
            "productInformation": {
                "size": int(size),
                "productType": typecode,
                "processingDate": processed,
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
                    "href": "/measurements/%s" % measurement_file,
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
