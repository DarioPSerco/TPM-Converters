"""JSON metadata emitter for QuickBird-2 products.

Builds a GeoJSON ``Feature`` manifest conformant to
``schema/quickbird.schema.json``, from a populated eoSip_converter ``Metadata``
object produced by ``product_quickbird.Product_Quickbird.extractMetadata``.

STRUCTURE is borrowed from the WorldView EOPF-EOS template
(``schema/worldview.schema.json``). VALUES are QuickBird-2's own — every field
is sourced either from this mission's extraction (the metadata dict) or from
this mission's config ([Mission-specific-values] in ingest_quickbird.cfg,
captured in ``QUICKBIRD_PROFILE`` below). NO WorldView values are used. See
``quickbird_fields.md``.

Near-identical to geoeye1_json/json_emitter.py (same Product_Directory base);
the only differences are the mission profile and the MP type set.

This replaces the XML / eoSIP .SIP.ZIP output stage. No XML / no eoSIP.
"""
import json
import os
import re

from eoSip_converter.esaProducts import metadata as M

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "schema", "quickbird.schema.json")

# QuickBird-2 mission profile — values from ingest_quickbird.cfg [Mission-specific-values].
# (Not read from the metadata object so the emitter also works standalone in tests.)
QUICKBIRD_PROFILE = {
    "platformShortName": "QuickBird-2",     # cfg METADATA_PLATFORM=QuickBird + METADATA_PLATFORM_ID=2; satId QB02
    "platformSerialIdentifier": 2,          # cfg METADATA_PLATFORM_ID=2
    "sensorType": "OPTICAL",                # cfg METADATA_SENSOR_TYPE=OPTICAL
    "instrumentShortName": "BGI",           # cfg METADATA_INSTRUMENT=BGI
    "status": "ARCHIVED",                   # cfg METADATA_STATUS=ARCHIVED
    "acquisitionType": "NOMINAL",           # cfg METADATA_ACQUISITION_TYPE=NOMINAL
    "referenceSystemIdentifier": "http://www.opengis.net/def/crs/EPSG/0/4326",  # cfg METADATA_REFERENCE_SYSTEM_IDENTIFIER=EPSG:4326
    "processStepDescription": "EOPF-EOS Converter for QuickBird-2",
    "referenceTitle": "EOSIP Specialization for QuickBird-2 products v1.2",  # cfg METADATA_SIP_SPEC_NAME_VERSION
    "referenceEdition": "1.2",
    "softwareTitle": "eoProdGen",           # cfg METADATA_SIP_SOFTWARE_NAME=eoProdGen
    "softwareEdition": "015",               # cfg METADATA_SIP_SOFTWARE_VERSION=015
    "processorPartyName": "ESA",            # cfg METADATA_RESPONSIBLE=ESA / METADATA_CREATOR=ESA
    "processorPartyType": "CI_Organisation",
}

# QuickBird-2 product types whose geometry is null and which carry a bbox
# (product_quickbird.WITH_BOUNDINGBOX).
MP_TYPES = {"BGI_PAN_MP", "BGI_4B__MP"}

# generic (non-mission) structural constants
LINK_MEASUREMENT_TYPE = "image/tiff"        # QuickBird-2 native imagery is GeoTIFF (.TIF)
LINK_MEASUREMENT_TITLE = "Native EO Product"
LINK_MEASUREMENT_CATEGORY = "DATA"
LINK_PREVIEW_TYPE = "image/png"
LINK_PREVIEW_TITLE = "Preview Image"
LINK_PREVIEW_CATEGORY = "OVERVIEW"


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


def _bbox_west_south_east_north(bbox_str):
    toks = [float(t) for t in str(bbox_str).split() if t != ""]
    lats = toks[0::2]
    lons = toks[1::2]
    return [min(lons), min(lats), max(lons), max(lats)]


def build_feature(met, product, eo_product_name, profile=QUICKBIRD_PROFILE,
                  native_product_name=None):
    """Build the GeoJSON Feature dict for a QuickBird-2 product."""
    typecode = _gv(met, M.METADATA_TYPECODE)
    is_mp = typecode in MP_TYPES
    native_name = native_product_name or getattr(product, "origName", None) or eo_product_name

    created = _norm_dt(_gv(met, M.METADATA_DATASET_PRODUCTION_DATE))
    begin = _norm_dt(_gv(met, M.METADATA_START_DATE_TIME))
    end = _norm_dt(_gv(met, M.METADATA_STOP_DATE_TIME)) or begin

    geometry = None
    bbox = None
    footprint = _gv(met, M.METADATA_FOOTPRINT)
    if is_mp:
        ba = _local_attr(met, "boundingBox")
        if ba is not None:
            bbox = _bbox_west_south_east_north(ba)
    elif footprint is not None:
        geometry = {"type": "Polygon", "coordinates": _polygon_coordinates(footprint)}

    acq_params = {
        "acquisitionType": profile["acquisitionType"],
        "beginningDateTime": begin,
        "endingDateTime": end,
        "operationalMode": _gv(met, M.METADATA_SENSOR_OPERATIONAL_MODE),  # native 'PAN' / 'PM'
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

    platform = {"platformShortName": profile["platformShortName"]}
    if profile.get("platformSerialIdentifier") is not None:
        platform["platformSerialIdentifier"] = profile["platformSerialIdentifier"]
    # orbitType: WorldView-schema slot has no QuickBird-2 extraction source -> omitted (gap)

    instrument = {
        "sensorType": profile["sensorType"],
        "instrumentShortName": profile["instrumentShortName"],
    }

    size = getattr(product, "tmpSize", 0) or 0
    product_info = {
        "productType": typecode,
        "size": int(size),
        "resourceLineage": {
            "processStep": {
                "description": profile["processStepDescription"],
                "stepDateTime": {"created": created},
                "processor": {
                    "role": "processor",
                    "party": {"name": profile["processorPartyName"], "type": profile["processorPartyType"]},
                },
                "reference": {"title": profile["referenceTitle"], "edition": profile["referenceEdition"]},
                "source": {
                    "sourceCitation": {"title": native_name},
                    "processedLevel": (_gv(met, M.METADATA_PROCESSING_LEVEL) or "").replace("other: ", "").strip() or None,
                },
                "processingInformation": {
                    "softwareReference": {"title": profile["softwareTitle"], "edition": profile["softwareEdition"]},
                },
                "output": {"sourceCitation": {"title": "%s.ZIP" % eo_product_name}},
            }
        },
    }
    if is_mp:
        product_info["referenceSystemIdentifier"] = profile["referenceSystemIdentifier"]
    level_token = typecode.split("_")[-1] if typecode else None
    if level_token:
        product_info["processingLevel"] = level_token  # QuickBird-2's own typecode level token
    cloud = _gv(met, M.METADATA_CLOUD_COVERAGE)
    if cloud is not None and str(cloud) != "-999":
        product_info["cloudCover"] = float(cloud)

    links = {
        "measurements": [{
            "href": native_name,
            "type": LINK_MEASUREMENT_TYPE,
            "title": LINK_MEASUREMENT_TITLE,
            "category": LINK_MEASUREMENT_CATEGORY,
        }],
        "preview": [{
            "href": "%s.PNG" % eo_product_name,
            "type": LINK_PREVIEW_TYPE,
            "title": LINK_PREVIEW_TITLE,
            "category": LINK_PREVIEW_CATEGORY,
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
            "status": profile["status"],
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
    import jsonschema
    jsonschema.validate(instance=feature, schema=load_schema(schema_path))
    return True


def write_json(feature, out_dir, eo_product_name, do_validate=True):
    if do_validate:
        validate(feature)
    out_path = os.path.join(out_dir, "%s.JSON" % eo_product_name)
    with open(out_path, "w", encoding="utf-8") as fd:
        json.dump(feature, fd, indent=2, ensure_ascii=False)
    return out_path


def emit(met, product, eo_product_name, out_dir, do_validate=True, **kwargs):
    feature = build_feature(met, product, eo_product_name, **kwargs)
    return write_json(feature, out_dir, eo_product_name, do_validate=do_validate)
