"""JSON metadata emitter for WorldView products.

Builds a GeoJSON ``Feature`` manifest conformant to
``schema/worldview.schema.json`` (derived from 'EOPF-EOS Specialization for
WorldView Products - v1.0D'), from a populated eoSip_converter ``Metadata``
object produced by ``product_worldview.Product_Worldview.extractMetadata``.

This replaces the XML / eoSIP .SIP.ZIP output stage of the original converter.
No XML and no eoSIP packaging is produced anywhere in this module.

Field-by-field provenance and every flagged conflict / OCR-suspect value are
documented in ``worldview_fields.md``.
"""
import json
import os
import re

from eoSip_converter.esaProducts import metadata as M

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "schema", "worldview.schema.json")

# spec-fixed values (EOPF-EOS WorldView spec v1.0D)
STATUS = "NOMINAL"
ORBIT_TYPE = "LEO"
SENSOR_TYPE = "OPTICAL"
ACQUISITION_TYPE = "NOMINAL"
PROCESS_STEP_DESCRIPTION = "EOPF-EOS Converter for WorldView"
PROCESSOR_ROLE = "processor"
PROCESSOR_PARTY_NAME = "External Data Handling for TPM"
PROCESSOR_PARTY_TYPE = "CI_Organisation"
REFERENCE_TITLE = "EOPF-EOS Specialization for WorldView products"
REFERENCE_EDITION = "1.0"
SOFTWARE_TITLE = "EOPF-EOS Converter for WorldView"
DEFAULT_REFERENCE_SYSTEM = "http://www.opengis.net/def/crs/EPSG/0/4326"

MEASUREMENT_TYPE = "application/x-hdf5"      # spec Table 19 fixed (FLAGGED: WV native is GeoTIFF)
MEASUREMENT_TITLE = "Native EO Product"
MEASUREMENT_CATEGORY = "DATA"
PREVIEW_TYPE = "image/png"
PREVIEW_TITLE = "Preview Image"
PREVIEW_CATEGORY = "OVERVIEW"

# product types whose geometry is null and which carry a bbox (spec Tables 3/4/14)
MP_TYPES = {"WV6_PAN_MP", "WV1_PAN_MP", "WV1_4B__MP", "WV1_8B__MP", "WV1_S8B_MP"}

# native instrument label (METADATA_INSTRUMENT) -> spec instrumentShortName (Table 9)
INSTRUMENT_SHORTNAME = {
    "WV60": "WorldView-60 Camera",
    "WV110": "WorldView-110 Camera",
    "SpaceView-110": "SpaceView-110 Camera",
    "WorldView Legion Camera": "WorldView Legion Camera",
}


def _gv(met, key):
    v = met.getMetadataValue(key)
    if not met.valueExists(v):
        return None
    return v


def _local_attr(met, name):
    for d in getattr(met, "localAttributes", []) or []:
        if isinstance(d, dict) and name in d:
            return d[name]
    return None


def _norm_dt(s):
    """Normalise a datetime string to RFC 3339 with millisecond precision + Z."""
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
    """footprint = 'lat lon lat lon ...' (closed ring) -> [[[lon, lat], ...]]."""
    toks = [t for t in str(footprint).split() if t != ""]
    ring = []
    for i in range(0, len(toks) - 1, 2):
        lat = float(toks[i])
        lon = float(toks[i + 1])
        ring.append([lon, lat])
    return [ring]


def _bbox_west_south_east_north(bbox_str):
    """boundingBox local attribute = 'lat lon lat lon ...' -> [W, S, E, N]."""
    toks = [float(t) for t in str(bbox_str).split() if t != ""]
    lats = toks[0::2]
    lons = toks[1::2]
    return [min(lons), min(lats), max(lons), max(lats)]


def _platform_short_name(met, is_legion):
    if is_legion:
        return "WorldView Legion"
    pid = _gv(met, M.METADATA_PLATFORM_ID)
    return "WorldView-%s" % pid if pid is not None else None


def _operational_mode(met, product):
    """INFERRED native->spec operationalMode (spec Table 2 association is OCR-garbled).

    Mapping by band count, with a STEREO override when the native processed
    level denotes a stereo product. FLAGGED in worldview_fields.md.
    """
    processed = _gv(met, M.METADATA_PROCESSING_LEVEL) or ""
    if "Stereo" in processed:
        return "STEREO"
    nb = _gv(met, "numberOfBands")
    try:
        nb = int(float(nb))
    except (TypeError, ValueError):
        nb = None
    if nb == 1:
        return "PANCHROMATIC"
    if nb in (3, 4):
        return "MS4B"
    if nb == 8:
        return "MS8B"
    return None


def _processing_level(met):
    """INFERRED productInformation.processingLevel from the typecode level token.

    Spec enum (1B/2A/3) is OCR-suspect and reviewer-disputed. Only the
    unambiguous tokens are mapped; others are omitted. FLAGGED.
    """
    typecode = _gv(met, M.METADATA_TYPECODE) or ""
    level = typecode.split("_")[-1] if typecode else ""
    return {"2A": "2A", "MP": "3"}.get(level)


def _processed_level(met):
    raw = _gv(met, M.METADATA_PROCESSING_LEVEL)
    if raw is None:
        return None
    return raw.replace("other: ", "").strip()


def build_feature(met, product, eo_product_name,
                  reference_system_identifier=DEFAULT_REFERENCE_SYSTEM,
                  converter_version="1.0.0",
                  native_product_name=None):
    """Build the GeoJSON Feature dict for a WorldView product."""
    is_legion = bool(getattr(product, "is_wv_legion", False))
    typecode = _gv(met, M.METADATA_TYPECODE)
    is_mp = typecode in MP_TYPES
    native_name = native_product_name or getattr(product, "origName", None) or eo_product_name

    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    # geometry / bbox
    geometry = None
    bbox = None
    footprint = _gv(met, M.METADATA_FOOTPRINT)
    if is_mp:
        geometry = None
        ba = _local_attr(met, "boundingBox")
        if ba is not None:
            bbox = _bbox_west_south_east_north(ba)
    elif footprint is not None:
        geometry = {"type": "Polygon", "coordinates": _polygon_coordinates(footprint)}

    # acquisitionParameters
    acq_params = {
        "acquisitionType": ACQUISITION_TYPE,
        "beginningDateTime": begin,
        "endingDateTime": end,
        "operationalMode": _operational_mode(met, product),
        "resolution": float(_gv(met, M.METADATA_RESOLUTION)),
        "acquisitionAngles": {
            "illuminationAzimuthAngle": float(_gv(met, M.METADATA_SUN_AZIMUTH)),
            "illuminationElevationAngle": float(_gv(met, M.METADATA_SUN_ELEVATION)),
        },
    }
    wrs_lon = _gv(met, M.METADATA_WRS_LONGITUDE_DEG_NORMALISED)
    wrs_lat = _gv(met, M.METADATA_WRS_LATITUDE_DEG_NORMALISED)
    if wrs_lon is not None:
        acq_params["wrsLongitudeGrid"] = wrs_lon
    if wrs_lat is not None:
        acq_params["wrsLatitudeGrid"] = wrs_lat

    # platform
    platform = {"platformShortName": _platform_short_name(met, is_legion), "orbitType": ORBIT_TYPE}
    if not is_legion:
        pid = _gv(met, M.METADATA_PLATFORM_ID)
        if pid is not None:
            platform["platformSerialIdentifier"] = int(pid)

    # instrument
    instrument_native = _gv(met, M.METADATA_INSTRUMENT)
    instrument = {
        "sensorType": SENSOR_TYPE,
        "instrumentShortName": INSTRUMENT_SHORTNAME.get(instrument_native, instrument_native),
    }

    # productInformation
    size = getattr(product, "tmpSize", 0) or 0
    product_info = {
        "productType": typecode,
        "size": int(size),
        "resourceLineage": {
            "processStep": {
                "description": PROCESS_STEP_DESCRIPTION,
                "stepDateTime": {"created": created},
                "processor": {
                    "role": PROCESSOR_ROLE,
                    "party": {"name": PROCESSOR_PARTY_NAME, "type": PROCESSOR_PARTY_TYPE},
                },
                "reference": {"title": REFERENCE_TITLE, "edition": REFERENCE_EDITION},
                "source": {
                    "sourceCitation": {"title": native_name},
                    "processedLevel": _processed_level(met),
                },
                "processingInformation": {
                    "softwareReference": {"title": SOFTWARE_TITLE, "edition": converter_version},
                },
                "output": {"sourceCitation": {"title": "%s.ZIP" % eo_product_name}},
            }
        },
    }
    if is_mp and reference_system_identifier:
        product_info["referenceSystemIdentifier"] = reference_system_identifier
    proc_level = _processing_level(met)
    if proc_level is not None:
        product_info["processingLevel"] = proc_level
    cloud = _gv(met, M.METADATA_CLOUD_COVERAGE)
    if cloud is not None and str(cloud) != "-999":
        product_info["cloudCover"] = float(cloud)

    # links
    preview_name = "%s.PNG" % eo_product_name
    links = {
        "measurements": [{
            "href": native_name,
            "type": MEASUREMENT_TYPE,
            "title": MEASUREMENT_TITLE,
            "category": MEASUREMENT_CATEGORY,
        }],
        "preview": [{
            "href": preview_name,
            "type": PREVIEW_TYPE,
            "title": PREVIEW_TITLE,
            "category": PREVIEW_CATEGORY,
        }],
    }

    feature = {
        "type": "Feature",
        "id": eo_product_name,
        "geometry": geometry,
        "properties": {
            "title": eo_product_name,
            "date": "%s/%s" % (begin, end),
            "created": created,
            "status": STATUS,
            "acquisitionInformation": {
                "platform": platform,
                "instrument": instrument,
                "acquisitionParameters": acq_params,
            },
            "productInformation": product_info,
            "links": links,
        },
    }
    if bbox is not None:
        feature["bbox"] = bbox
    return feature


def load_schema(schema_path=SCHEMA_PATH):
    with open(schema_path, "r", encoding="utf-8") as fd:
        return json.load(fd)


def validate(feature, schema_path=SCHEMA_PATH):
    """Validate a feature against the WorldView schema. Raises on failure."""
    import jsonschema
    jsonschema.validate(instance=feature, schema=load_schema(schema_path))
    return True


def write_json(feature, out_dir, eo_product_name, do_validate=True):
    """Validate (optional) then write <eo_product_name>.JSON to out_dir."""
    if do_validate:
        validate(feature)
    out_path = os.path.join(out_dir, "%s.JSON" % eo_product_name)
    with open(out_path, "w", encoding="utf-8") as fd:
        json.dump(feature, fd, indent=2, ensure_ascii=False)
    return out_path


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    """Build, validate and write the JSON manifest. Returns the output path."""
    feature = build_feature(met, product, eo_product_name, **kwargs)
    return write_json(feature, out_dir, eo_product_name, do_validate=do_validate)
