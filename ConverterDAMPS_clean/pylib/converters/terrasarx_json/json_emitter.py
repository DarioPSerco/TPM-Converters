"""JSON metadata emitter for TerraSAR-X / TanDEM-X products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps TerraSAR-X's own extraction (the
metadata dict populated by
``product_terrasarx.Product_TerraSARX.extractMetadata``), declares the
mission-fixed value map, and hands both layers to the mission-agnostic
generator. Output follows "EOPF-EOS SPECIALIZATION FOR TERRASAR-X / TANDEM-X
PRODUCTS" 1.01 through its own placeholder template
(``feature_template_tsx.json``).

Spec readings encoded here:
- product types: the Table 1 / Table 2 codes as written, including
  L1BSL__MGC for the spotlight MGD product.
- platform / instrument (Tables 9-10): TerraSAR-X / TSX-1 for a TSX-1
  product, TanDEM-X / TOR for a TDX-1 product, the two listed values in
  order.
- polarisationMode (Table 11): SINGLE / DUAL / TWIN / QUAD -> S / D / T / Q
  (the table's own descriptions of T and Q are copy errors).
- wavelengths: one X-band entry, ``discreteWavelengths`` (Table 14, an
  array) fixed to 31.0666E-03 m.
- resolution: the spec gives no rule; the worse (larger) of the ground range
  and azimuth resolutions is used, as for COSMO-SkyMed and RADARSAT-1.
- referenceSystemIdentifier (mandatory): the UTM / UPS zone (WGS84) of the
  geocoded GEC / EEC product; EPSG:4326 for SSC / MGD products, whose scene
  corners are geodetic.
- lineage source: Table 16 is normative (``source[0].sourceCitation.title``),
  not the example (``source[0].citation``). The citation is the main
  annotation file name, so the packager and run_mission.py find the native
  product back.
- wrsLatitudeGrid: in the example only, not in the tables; not written.
- links: titles fixed by Tables 18-19 ("Native EO Product", "Preview Image");
  the native product folder is stored as ``measurements/<product name>/`` and
  the link points at its first image data file (GeoTIFF, or COSAR as
  ``application/octet-stream``).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from terrasarx_json import __version__
from terrasarx_json import product_terrasarx as P

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_tsx.json"

# spec Table 14: X-band, fixed wavelength (m)
SPECTRAL_RANGE = "X"
DISCRETE_WAVELENGTHS = [31.0666e-3]

# TerraSAR-X mission-fixed values - template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"orbitType": "LEO"},
            "instrument": {"sensorType": "RADAR"},
            "acquisitionParameters": [{
                "wavelengths": [{
                    "spectralRange": SPECTRAL_RANGE,
                    "discreteWavelengths": DISCRETE_WAVELENGTHS,
                }],
            }],
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for TerraSAR-X and TanDEM-X",
                "reference": {"title": "EOPF-EOS Specialization for TerraSAR-X and TanDEM-X products",
                              "edition": "1.01"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for TerraSAR-X and TanDEM-X",
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
    """TerraSAR-X per-product dynamic values, from this mission's extraction."""
    # lineage citation: the entry file (the main annotation) as delivered;
    # measurements link: the first image data file
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
                "platform": {"platformShortName": _gv(met, M.METADATA_PLATFORM)},
                "instrument": {"instrumentShortName": _gv(met, M.METADATA_INSTRUMENT)},
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
