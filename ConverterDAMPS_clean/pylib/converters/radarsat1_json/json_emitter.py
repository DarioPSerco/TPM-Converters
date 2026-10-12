"""JSON metadata emitter for RADARSAT-1 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps RADARSAT-1's own extraction (the
metadata dict populated by
``product_radarsat1.Product_Radarsat1.extractMetadata``), declares the
mission-fixed value map, and hands both layers to the mission-agnostic
generator. Output follows "EOPF-EOS SPECIALIZATION FOR RADARSAT-1 PRODUCTS"
1.01 through its own placeholder template (``feature_template_rs1.json``).

Spec readings encoded here:
- product types: the scope list and Table 1 name the Standard Beam SLC / SSG
  products L1_SB__SLC / L2_SB__SSG, Table 2 and the example manifest
  (productType) name them L1_BM__SLC / L2_BM__SSG. Table 2 is used: it is the
  product type characterization, and BM is the operationalMode it gives for
  those products.
- operationalMode: the Table 2 codes (BM, BSW, BMF, BS, SCN, SCW), not the
  example's "Standard Beam".
- wavelengths: one C-band entry, ``discreteWavelength`` (Table 14, a Double)
  fixed to 56.5646E-03 m, not the example's ``discreteWavelengths`` array.
- resolution: the spec gives no rule; the worse (larger) of the nominal range
  and azimuth resolutions is used, as for COSMO-SkyMed.
- referenceSystemIdentifier (mandatory): the UTM zone (WGS84) of the geocoded
  SSG product; EPSG:4326 for the other products, whose corner coordinates are
  geodetic.
- lineage source: Table 17 is normative (``source[0].sourceCitation.title``),
  not the example (``source[0].citation``).
- links: titles fixed by Tables 19-20 ("Native EO Product", "Preview Image"),
  not the example's; the overview sits under ``previews/overviews/`` as the
  spec's package description and Table 20 example require.
- measurements: the link points at the CEOS image data file (``.sard``), with
  media type ``application/octet-stream`` (no registered type for CEOS).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from radarsat1_json import __version__
from radarsat1_json import product_radarsat1 as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_rs1.json"

# spec Table 14: C-band, fixed wavelength (m)
SPECTRAL_RANGE = "C"
DISCRETE_WAVELENGTH = 56.5646e-3

# RADARSAT-1 mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"platformShortName": "RADARSAT-1", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "SAR", "sensorType": "RADAR"},
            "acquisitionParameters": [{
                "wavelengths": [{
                    "spectralRange": SPECTRAL_RANGE,
                    "discreteWavelength": DISCRETE_WAVELENGTH,
                }],
            }],
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for RADARSAT-1",
                "reference": {"title": "EOPF-EOS Specialization for RADARSAT-1 products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for RADARSAT-1",
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
    """RADARSAT-1 per-product dynamic values, from this mission's extraction."""
    # lineage citation: the entry file (the CEOS volume directory) as
    # delivered; measurements link: the image data file
    native_name = (native_product_name
                   or getattr(product, "origName", None)
                   or eo_product_name)
    measurement_file = _la(met, "nativeDataFile") or native_name
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _gv(met, M.METADATA_DATASET_PRODUCTION_DATE)
    begin = _gv(met, M.METADATA_START_DATE_TIME)
    end = _gv(met, M.METADATA_STOP_DATE_TIME) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

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
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "polarisationMode": _gv(met, M.METADATA_POLARISATION_MODE),
                    "polarisationChannels": _gv(met, M.METADATA_POLARISATION_CHANNELS),
                    "antennaLookDirection": _gv(met, M.METADATA_ANTENNA_LOOK_DIRECTION),
                    "azimuthResolution": _float_or_none(_la(met, "azimuthResolution")),
                    "rangeResolution": _float_or_none(_la(met, "rangeResolution")),
                    "resolution": _float_or_none(_la(met, "resolution")),
                    "acquisitionAngles": {"incidenceAngle": incidence},
                    "orbitNumber": _int_or_none(_gv(met, M.METADATA_ORBIT)),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                }],
            }],
            "productInformation": {
                "size": int(size),
                "productType": typecode,
                "referenceSystemIdentifier": _la(met, "referenceSystemIdentifier"),
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
                    "href": "/measurements/%s" % measurement_file,
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
