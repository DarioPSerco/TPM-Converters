"""JSON metadata emitter for ICEYE products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps ICEYE's own extraction (the metadata
dict populated by ``product_iceye.Product_Iceye.extractMetadata``), declares
the ICEYE mission-fixed value map, and hands both layers to the
mission-agnostic generator. Output follows "EOPF-EOS SPECIALIZATION FOR
ICEYE PRODUCTS" 1.0.

ICEYE is SAR: its template carries fields the optical missions don't
(orbit, polarisation, antennaLookDirection, azimuth/range resolution,
incidenceAngle) and lacks the optical ones (cloudCover, illumination angles).
The overlay can add keys but never remove them, so this mission uses its own
placeholder template (``feature_template_sar.json``) through the generator's
existing ``template_path`` extension point — no change to the common core.

Spec readings encoded here:
- product types: Tables 1-2 are normative (L1_SC__GRD for Scan); Tables 10
  and 14 name it L1_SR__GRD, read as the same product.
- resolution: Table 10 fixes it per product type (3 / 1 / 15 m);
  azimuthResolution and rangeResolution carry the native measured values
  (azimuth_resolution / range_resolution_center, else the pixel spacing).
- polarisationChannels, orbitNumber, orbitDirection: names from Tables 10 and
  12 (camelCase), flat under acquisitionParameters[0] as for COSMO-SkyMed; the
  example's ``polarisationChannel`` / ``orbitParameters`` are not used.
- wavelengths: one X-band entry, discreteWavelength fixed by Table 14.
- processingLevel / processedLevel: SLC -> 1A / L1A, GRD -> 1B / L1B.
- referenceSystemIdentifier: written when the native geo_ref_system is
  WGS84; Table 14 makes it mandatory for GRD - a missing CRS there fails.
- lineage source: Table 16 is normative (``source[0].sourceCitation.title``).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import os
import re
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from iceye_json import __version__

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_sar.json"

# spec Table 14: X-band, fixed wavelength (m)
SPECTRAL_RANGE = "X"
DISCRETE_WAVELENGTH = 31.0666e-3

# spec Table 10: resolution (m) per product type
RESOLUTION = {"L1_SM__SLC": 3.0, "L1_SM__GRD": 3.0,
              "L1_SL__SLC": 1.0, "L1_SL__GRD": 1.0,
              "L1_SC__GRD": 15.0}

# spec Tables 15-16: native level -> (processingLevel, processedLevel code)
LEVELS = {"SLC": ("1A", "L1A"), "GRD": ("1B", "L1B")}

# spec Table 14: product types that must carry referenceSystemIdentifier
CRS_MANDATORY = ("L1_SM__GRD", "L1_SL__GRD", "L1_SC__GRD")

# ICEYE mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"platformShortName": "ICEYE", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "SAR", "sensorType": "RADAR"},
            "acquisitionParameters": [{"wavelengths": [{
                "spectralRange": SPECTRAL_RANGE,
                "discreteWavelength": DISCRETE_WAVELENGTH,
            }]}],
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for ICEYE",
                "reference": {"title": "EOPF-EOS Specialization for ICEYE products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for ICEYE",
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


def _serial_or_none(value):
    """spec Table 8: platformSerialIdentifier is an Integer ("X2" -> 2)."""
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _native_image(product):
    """The image file of the native product (GeoTIFF for GRD, HDF5 for SLC);
    the package stores the native folder content at measurements/."""
    folder = getattr(product, "EO_FOLDER", None)
    if not folder or not os.path.isdir(folder):
        return None
    names = sorted(os.listdir(folder))
    for ext in (".tif", ".tiff", ".h5"):
        for name in names:
            if name.lower().endswith(ext):
                return name
    return None


def _measurements_type(native_file):
    name = (native_file or "").lower()
    if name.endswith(".tif") or name.endswith(".tiff"):
        return "image/tiff; application=geotiff"
    if name.endswith(".h5"):
        return "application/x-hdf5"
    return None


def _norm_dt(s):
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$", s)
    if not m:
        return s
    base, frac = m.group(1), m.group(2)
    millis = (frac + "000")[:3] if frac else "000"
    return "%s.%sZ" % (base, millis)


def _polygon_coordinates(footprint):
    toks = [t for t in str(footprint).split() if t != ""]
    ring = []
    for i in range(0, len(toks) - 1, 2):
        ring.append([float(toks[i + 1]), float(toks[i])])  # [lon, lat]
    return [ring]


def build_layers(met, product, eo_product_name, native_product_name=None):
    """ICEYE per-product dynamic values, from this mission's extraction."""
    native_name = (native_product_name
                   or getattr(product, "productFolderName", None)
                   or eo_product_name)
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE)
                       or _gv(met, M.METADATA_PROCESSING_TIME))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

    processed_date = _norm_dt(_gv(met, M.METADATA_PROCESSING_TIME)) or created
    orbit = _gv(met, M.METADATA_ORBIT)
    incidence = _gv(met, M.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
    # native measured resolution, else the pixel spacing set by refineMetadata
    azimuth_res = (_float_or_none(_gv(met, "azimuth_resolution"))
                   or _float_or_none(met.getLocalAttributeValue("azimuthResolution")))
    range_res = (_float_or_none(_gv(met, "range_resolution_center"))
                 or _float_or_none(met.getLocalAttributeValue("rangeResolution")))
    serial = _gv(met, M.METADATA_SATELLITE)
    level, level_code = LEVELS.get(_gv(met, "level"), (None, None))
    crs = ("http://www.opengis.net/def/crs/EPSG/0/4326"
           if _gv(met, "geo_ref_system") == "WGS84" else None)
    if crs is None and typecode in CRS_MANDATORY:
        raise ValueError("referenceSystemIdentifier is mandatory for %s but the native "
                         "geo_ref_system is %r" % (typecode, _gv(met, "geo_ref_system")))
    native_file = _native_image(product)
    size = getattr(product, "tmpSize", 0) or 0

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{
                "platform": {"platformSerialIdentifier": _serial_or_none(serial)},
                "acquisitionParameters": [{
                    "beginningDateTime": begin,
                    "endingDateTime": end,
                    "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),
                    "polarisationMode": _gv(met, M.METADATA_POLARISATION_MODE),
                    "polarisationChannels": _gv(met, M.METADATA_POLARISATION_CHANNELS),
                    "antennaLookDirection": _gv(met, M.METADATA_ANTENNA_LOOK_DIRECTION),
                    "azimuthResolution": azimuth_res,
                    "rangeResolution": range_res,
                    "resolution": RESOLUTION.get(typecode),
                    "orbitNumber": _int_or_none(orbit),
                    "orbitDirection": _gv(met, M.METADATA_ORBIT_DIRECTION),
                    "acquisitionAngles": {
                        "incidenceAngle": float(incidence) if incidence is not None else None,
                    },
                }],
            }],
            "productInformation": {
                "size": int(size),
                "productType": typecode,
                "referenceSystemIdentifier": crs,
                "processingDate": processed_date,
                "processingLevel": level,
                "resourceLineage": [{"processStep": [{
                    "stepDateTime": {"created": created},
                    "source": [{"sourceCitation": {"title": native_name},
                                "processedLevel": {"code": level_code}}],
                    "output": [{"sourceCitation": {"title": "%s.ZIP" % eo_product_name}}],
                }]}],
            },
            "links": {
                "measurements": [{"href": "/measurements/%s" % native_file if native_file else None,
                                  "type": _measurements_type(native_file)}],
                "preview": [{"href": "/preview/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
