"""JSON metadata emitter for QuickBird-2 products.

Mission adapter for the common template-driven generator
(``common/json_template.py``). Keeps QuickBird-2's own extraction (the
metadata dict populated by ``product_quickbird.Product_Quickbird.
extractMetadata``), declares the QuickBird-2 mission-fixed value map, and
hands both layers to the mission-agnostic generator. Output follows
"EOPF-EOS SPECIALIZATION FOR QUICKBIRD-2 PRODUCTS" 1.0 through its own
placeholder template (``feature_template_qb2.json``).

Spec readings encoded here:
- wavelengths: Table 10 and the example spell the block ``wavelenghts``,
  Table 13 (which defines its content) spells ``wavelengths``; the plural is used, as for WorldView and COSMO-SkyMed. One
  entry per spectralRange of Table 14: start/stop are the outer bounds of the
  range, discreteWavelengths the band centres.
- operationalMode: Table 2 gives PAN / MS4B per product type; Table 10 also
  allows STEREO, used (as in the example) for stereo native levels. Table 14
  gives STEREO the PAN or MS4B bands, so wavelengths follow the band set.
- lineage source: Table 17 is normative (``source[0].sourceCitation.title``),
  not the example (``source[0].citation``).
- cloudCover and referenceSystemIdentifier are written only when the native
  product carries them (Table 18; Table 15 makes the CRS mandatory only for
  L2AVRS_* and L3_* - a missing CRS there fails the conversion).

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import re
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M

from common import json_template
from quickbird_json import __version__

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template_qb2.json"

# QuickBird-2 mission-fixed values — template slots constant for this mission,
# shaped as a partial tree mirroring the template.
MISSION_VALUES = {
    "properties": {
        "acquisitionInformation": [{
            "platform": {"platformShortName": "QuickBird-2", "orbitType": "LEO"},
            "instrument": {"instrumentShortName": "BGI", "sensorType": "OPTICAL"},
        }],
        "productInformation": {
            "resourceLineage": [{"processStep": [{
                "description": "EOPF-EOS Converter for QuickBird-2",
                "reference": {"title": "EOPF-EOS Specialization for QuickBird-2 products",
                              "edition": "1.0"},
                "processingInformation": {"softwareReference": {
                    "title": "EOPF-EOS Converter for QuickBird-2",
                    "edition": __version__}},
            }]}],
        },
    },
}


# spec Table 14, in nm: band set -> [(spectralRange, [(start, stop), ...])]
WAVELENGTHS_NM = {
    "PAN": [("VNIR", [(450, 900)])],
    "MS4B": [("VIS", [(450, 520), (520, 600), (630, 690)]),
             ("NIR", [(760, 900)])],
}

# spec Table 16: native level -> processingLevel ("3" for every other level)
PROCESSING_LEVEL = {"LV1B": "1B", "Stereo1B": "1B",
                    "LV2A": "2A", "Stereo2A": "2A", "StereoOR2A": "2A"}

# spec Table 15: product types that must carry referenceSystemIdentifier
CRS_MANDATORY = ("L2AVRS_PAN", "L2AVRS_MS_", "L3_MRO_PAN", "L3_MRP_MS_")


def _gv(met, key):
    v = met.getMetadataValue(key)
    if not met.valueExists(v):
        return None
    return v


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


def _band_set(typecode):
    """PAN / MS4B from the product type band token (Table 2)."""
    if not typecode:
        return None
    return "PAN" if typecode.endswith("PAN") else "MS4B"


def _wavelengths(band_set):
    ranges = WAVELENGTHS_NM.get(band_set)
    if ranges is None:
        return None
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands) / 1e9,
        "stopWavelength": max(b[1] for b in bands) / 1e9,
        "discreteWavelengths": [(b[0] + b[1]) / 2 / 1e9 for b in bands],
    } for spectral_range, bands in ranges]


def _reference_system(met):
    """EPSG URI from the native map projection: WGS84 UTM -> 326zz/327zz,
    WGS84 geographic -> 4326. None when not derivable."""
    datum = (_gv(met, "datumName") or "").replace('"', "")
    proj = (_gv(met, "mapProjName") or "").replace('"', "")
    if datum != "WE":
        return None
    if proj == "UTM":
        zone = _gv(met, "mapZone")
        hemi = (_gv(met, "mapHemi") or "").replace('"', "")
        if zone is None or hemi not in ("N", "S"):
            return None
        code = (32600 if hemi == "N" else 32700) + int(zone)
    elif proj.startswith("Geographic"):
        code = 4326
    else:
        return None
    return "http://www.opengis.net/def/crs/EPSG/0/%d" % code


def build_layers(met, product, eo_product_name, native_product_name=None):
    """QuickBird-2 per-product dynamic values, from this mission's extraction."""
    native_name = native_product_name or getattr(product, "origName", None) or eo_product_name
    typecode = _gv(met, M.METADATA_TYPECODE)
    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    footprint = _gv(met, M.METADATA_FOOTPRINT)
    coordinates = _polygon_coordinates(footprint) if footprint is not None else None

    resolution = _gv(met, M.METADATA_RESOLUTION)
    sun_az = _gv(met, M.METADATA_SUN_AZIMUTH)
    sun_el = _gv(met, M.METADATA_SUN_ELEVATION)
    cloud = _gv(met, M.METADATA_CLOUD_COVERAGE)
    if cloud is not None and str(cloud) == "-999":
        cloud = None
    processed = (_gv(met, M.METADATA_PROCESSING_LEVEL) or "").replace("other: ", "").strip() or None
    processing_level = PROCESSING_LEVEL.get(processed, "3") if processed else None
    band_set = _band_set(typecode)
    operational_mode = "STEREO" if "Stereo" in (processed or "") else band_set
    size = getattr(product, "tmpSize", 0) or 0
    crs = _reference_system(met)
    if crs is None and typecode in CRS_MANDATORY:
        raise ValueError("referenceSystemIdentifier is mandatory for %s but the native "
                         "map projection gives none" % typecode)

    dynamic = {
        "id": eo_product_name,
        "geometry": {"coordinates": coordinates},
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end) if begin and end else None,
            "created": created,
            "acquisitionInformation": [{"acquisitionParameters": [{
                "beginningDateTime": begin,
                "endingDateTime": end,
                "operationalMode": operational_mode,
                "resolution": float(resolution) if resolution is not None else None,
                "wavelengths": _wavelengths(band_set),
                "acquisitionAngles": {
                    "illuminationAzimuthAngle": float(sun_az) if sun_az is not None else None,
                    "illuminationElevationAngle": float(sun_el) if sun_el is not None else None,
                },
            }]}],
            "productInformation": {
                "size": int(size),
                "cloudCover": float(cloud) if cloud is not None else None,
                "productType": typecode,
                "referenceSystemIdentifier": crs,
                "processingDate": created,
                "processingLevel": processing_level,
                "resourceLineage": [{"processStep": [{
                    "stepDateTime": {"created": created},
                    "source": [{"sourceCitation": {"title": native_name},
                                "processedLevel": {"code": processed}}],
                    "output": [{"sourceCitation": {"title": "%s.ZIP" % eo_product_name}}],
                }]}],
            },
            "links": {
                "measurements": [{"href": "/measurements/%s" % native_name}],
                "preview": [{"href": "/preview/overviews/%s.PNG" % eo_product_name}],
            },
        },
    }
    return MISSION_VALUES, json_template.prune(dynamic)


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    mission, dynamic = build_layers(met, product, eo_product_name, **kwargs)
    return json_template.emit(out_dir, eo_product_name, mission, dynamic,
                              template_path=TEMPLATE_PATH, do_validate=do_validate)
