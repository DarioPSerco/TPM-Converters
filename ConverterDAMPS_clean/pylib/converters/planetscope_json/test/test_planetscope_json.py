"""Structural proof: drive planetscope_json extraction on SYNTHETIC native
PlanetScope items, emit the JSON manifest via the common template generator,
and assert the output matches TDS/template/PSC-template.json key-path for
key-path - optical fields present, SAR fields absent, no placeholder left.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): no real
PlanetScope TDS product has been run yet. The visual item carries the values
of the specialization's own example manifest.
"""
import json
import os
from pathlib import Path

import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from planetscope_json import product_planetscope, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_psc"
ORDER_DIR = FIXTURE_DIR / "order_7d1c" / "PSScene"
VO_ID = "20170424_134911_0e19"
VO_JSON = ORDER_DIR / ("%s_metadata.json" % VO_ID)
SR_ID = "20210314_070803_29_2262"
SR_JSON = ORDER_DIR / ("%s_metadata.json" % SR_ID)
BASIC_ID = "20190801_093015_1018"
BASIC_JSON = FIXTURE_DIR / BASIC_ID / ("%s_metadata.json" % BASIC_ID)
OT_ID = "1234567_3357220_2017-04-24_0e19"
OT_JSON = FIXTURE_DIR / "ortho_tile" / OT_ID / ("%s_metadata.json" % OT_ID)
PSC_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "PSC-template.json"

# EO product names as the naming convention builds them
# (<MMM>_<CCCC>_<TTTTTTTTTT>_<start>_<stop>_<vvvv>)
VO_EO_NAME = "PSC_OPER_L3_VO__MS__20170424T134911_20170424T135111_0001"
SR_EO_NAME = "PSC_OPER_L3_SRO_MS__20210314T070803_20210314T070803_0001"
BASIC_EO_NAME = "PSC_OPER_L1BAB__MS__20190801T093015_20190801T093016_0001"
OT_EO_NAME = "PSC_OPER_L3_OT__MS__20170424T100500_20170424T100500_0001"

# the six product types the specialization allows (Table 2)
ALLOWED_PRODUCT_TYPES = {"L3_AO__MS_", "L3_SRO_MS_", "L1AAB__MS_", "L1BAB__MS_",
                         "L3_OT__MS_", "L3_VO__MS_"}

SAR_KEYS = ["polarisationMode", "polarisationChannel", "rangeResolution",
            "azimuthResolution", "antennaLookDirection", "orbitNumber"]
OTHER_MISSION_TOKENS = ["GeoEye", "WorldView", "QuickBird", "Pleiades", "ICEYE",
                        "COSMO", "RADAR", "X-Band"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(entry, work_folder):
    prod = product_planetscope.Product_Planetscope(str(entry))
    prod.setDebug(0)
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, _ProcessInfoStub(str(work_folder)))
    return prod, met


def _feature(entry, eo_name, work_folder):
    prod, met = _extract(entry, work_folder)
    # the ingester passes the entry file's basename, as here
    mission, dynamic = json_emitter.build_layers(
        met, prod, eo_name, native_product_name=os.path.basename(str(entry)))
    feature = json_template.build(mission, dynamic, template_path=json_emitter.TEMPLATE_PATH)
    return prod, met, feature


def _key_paths(node, prefix="$"):
    paths = set()
    if isinstance(node, dict):
        for k, v in node.items():
            paths |= _key_paths(v, "%s.%s" % (prefix, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            paths |= _key_paths(v, "%s[%d]" % (prefix, i))
    else:
        paths.add(prefix)
    return paths


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def test_emitted_json_matches_psc_template_structure(work):
    _, _, feature = _feature(VO_JSON, VO_EO_NAME, work)
    json_template.validate(feature)
    with open(PSC_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_visual_scene_values(work):
    prod, _, feature = _feature(VO_JSON, VO_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    par = acq["acquisitionParameters"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == VO_EO_NAME
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert len(ring) == 5 and ring[0] == ring[-1]
    assert ring[0] == [-66.44291264, -24.15261009]
    assert props["status"] == "ACQUIRED"
    assert props["title"] == VO_EO_NAME
    # XML gives whole seconds, the item JSON the milliseconds of the start
    assert props["date"] == "2017-04-24T13:49:11.806Z/2017-04-24T13:51:11.000Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "Dove", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "PS2", "sensorType": "OPTICAL"}
    assert par["beginningDateTime"] == "2017-04-24T13:49:11.806Z"
    assert par["endingDateTime"] == "2017-04-24T13:51:11.000Z"
    assert par["acquisitionType"] == "NOMINAL"
    assert par["operationalMode"] == "MS3B"
    assert par["resolution"] == 3.0
    assert par["orbitDirection"] == "DESCENDING"
    assert par["wavelengths"] == [{
        "spectralRange": "VIS", "startWavelength": 465e-9, "stopWavelength": 680e-9,
        "discreteWavelengths": [490e-9, 565e-9, 665e-9]}]
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "incidenceAngle": 0.7}

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_VO__MS_"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["processingDate"] == "2017-04-25T02:10:33.000Z"
    assert pinfo["cloudCover"] == 0.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"
    # only this item's files, not the other item sharing the folder
    assert pinfo["size"] == sum(p.stat().st_size for p in ORDER_DIR.glob(VO_ID + "_*"))
    assert len(prod.files) == 4

    step0, step1 = pinfo["resourceLineage"][0]["processStep"]
    assert step0["description"] == "PlanetScope processor"
    assert step0["processor"][0]["party"][0] == {"name": "Planet", "type": "CI_Organisation"}
    assert step0["source"] == [{"processedLevel": {"code": "L3B"}}]
    assert step0["processingInformation"]["softwareReference"] == {
        "title": "Planet Ortho Processor", "edition": "4.1.0"}
    assert step0["output"][0]["sourceCitation"]["title"] == VO_JSON.name
    assert step1["description"] == "EOPF-EOS Converter for PlanetScope"
    assert step1["stepDateTime"]["created"] == props["created"]
    assert step1["processor"][0]["party"][0]["name"] == "EOF-EOS External Data Handling"
    assert step1["reference"] == [{"title": "EOPF-EOS Specialization for PlanetScope products",
                                   "edition": "1.0"}]
    assert step1["source"][0]["sourceCitation"]["title"] == VO_JSON.name
    assert step1["source"][0]["processedLevel"]["code"] == "L3B"
    assert step1["processingInformation"]["softwareReference"]["title"] == \
        "EOPF-EOS Converter for PlanetScope"
    assert step1["output"][0]["sourceCitation"]["title"] == "%s.ZIP" % VO_EO_NAME

    links = props["links"]
    assert links["measurements"] == [{"href": "/measurements/%s_3B_Visual.tif" % VO_ID,
                                      "type": "image/tiff", "title": "Native EO Product",
                                      "category": "DATA"}]
    assert links["previews"] == [{"href": "/preview/overviews/%s.PNG" % VO_EO_NAME,
                                 "type": "image/png", "title": "Preview Image",
                                 "category": "OVERVIEW"}]


def test_superdove_8_band_surface_reflectance(work):
    _, _, feature = _feature(SR_JSON, SR_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    par = acq["acquisitionParameters"][0]
    assert acq["platform"]["platformShortName"] == "SuperDove"
    assert acq["instrument"]["instrumentShortName"] == "PSB.SD"
    assert par["operationalMode"] == "MS8B"
    assert [w["spectralRange"] for w in par["wavelengths"]] == ["VIS", "VNIR", "NIR"]
    assert len(par["wavelengths"][0]["discreteWavelengths"]) == 6
    assert par["wavelengths"][0]["startWavelength"] == 431e-9
    assert par["wavelengths"][1] == {"spectralRange": "VNIR", "startWavelength": 697e-9,
                                     "stopWavelength": 713e-9, "discreteWavelengths": [705e-9]}
    assert par["beginningDateTime"] == par["endingDateTime"] == "2021-03-14T07:08:03.311Z"
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_SRO_MS_"
    assert pinfo["cloudCover"] == 12.0
    assert props["links"]["measurements"][0]["href"] == \
        "/measurements/%s_3B_AnalyticMS_SR_8b.tif" % SR_ID


def test_legacy_layout_basic_scene(work):
    """Per-asset sub-folders, level 1B, no CRS, no cloud cover, clockwise
    footprint turned counter-clockwise."""
    prod, _, feature = _feature(BASIC_JSON, BASIC_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert props["acquisitionInformation"][0]["platform"]["platformShortName"] == "Dove-R"
    assert par["operationalMode"] == "MS4B"
    assert [w["spectralRange"] for w in par["wavelengths"]] == ["VIS", "NIR"]
    assert par["resolution"] == 3.7  # no pixel_resolution: gsd
    assert props["date"] == "2019-08-01T09:30:15.500Z/2019-08-01T09:30:16.250Z"

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1BAB__MS_"
    assert pinfo["processingLevel"] == "1B"
    assert "referenceSystemIdentifier" not in pinfo
    assert "cloudCover" not in pinfo
    steps = pinfo["resourceLineage"][0]["processStep"]
    assert steps[0]["source"][0]["processedLevel"]["code"] == "L1B"
    assert steps[1]["source"][0]["processedLevel"]["code"] == "L1B"

    ring = feature["geometry"]["coordinates"][0]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    assert area > 0, "footprint must be counter-clockwise (RFC 7946)"
    assert props["links"]["measurements"][0]["href"] == \
        "/measurements/basic_analytic_4b/%s_1B_AnalyticMS.tif" % BASIC_ID
    assert len(prod.files) == 4  # json + tif + xml + rpc


def test_ortho_tile_multipolygon(work):
    _, _, feature = _feature(OT_JSON, OT_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_OT__MS_"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["cloudCover"] == 5.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32633"
    assert pinfo["resourceLineage"][0]["processStep"][1]["source"][0]["processedLevel"]["code"] == "L3A"
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "MS4B"
    assert par["resolution"] == 3.125
    # MultiPolygon -> bounding box of all rings, as a Polygon
    assert feature["geometry"] == {"type": "Polygon", "coordinates": [[
        [15.0, 40.0], [15.3, 40.0], [15.3, 40.2], [15.0, 40.2], [15.0, 40.0]]]}


def test_lineage_citation_is_the_entry_file(work):
    """The runner and the packager find the native item back from it."""
    _, _, feature = _feature(SR_JSON, SR_EO_NAME, work)
    assert json_template.lineage_citation(feature) == SR_JSON.name


@pytest.mark.parametrize("entry,size", [(SR_JSON, (16, 12)), (VO_JSON, (16, 12)),
                                        (BASIC_JSON, (16, 12)), (OT_JSON, (16, 12))])
def test_overview_png(tmp_path, entry, size):
    prod = product_planetscope.Product_Planetscope(str(entry))
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))

    from PIL import Image
    with Image.open(png) as im:
        assert im.format == "PNG"
        assert im.mode == "RGBA"
        assert im.size == size
        # the zero (no-data) first column is transparent, the rest opaque
        assert im.getpixel((0, 5))[3] == 0
        assert im.getpixel((8, 5))[3] == 255


def test_visual_asset_preferred_for_overview():
    prod = product_planetscope.Product_Planetscope(str(VO_JSON))
    assert prod.visual_file is not None and prod.visual_file.endswith("_3B_Visual.tif")


def test_product_type_table_is_the_specialization_one():
    tables = product_planetscope.IMAGE_ASSETS + product_planetscope.ORTHO_TILE_ASSETS
    assert {row[1] for row in tables} == ALLOWED_PRODUCT_TYPES
    assert set(product_planetscope.ALLOWED_MODES) == ALLOWED_PRODUCT_TYPES
    for pattern, typecode, level, bands in tables:
        assert len(typecode) == 10, typecode
        assert product_planetscope.OPERATIONAL_MODE[bands] in product_planetscope.ALLOWED_MODES[typecode]
        assert level in product_planetscope.PROCESSING_LEVEL
    assert set(product_planetscope.WAVELENGTHS) == {"MS3B", "MS4B", "MS8B"}
    for mode, ranges in product_planetscope.WAVELENGTHS.items():
        assert sum(len(bands) for _, bands in ranges) == int(mode[2])


def test_entry_must_be_item_metadata(tmp_path):
    bogus = tmp_path / "manifest.json"
    bogus.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception, match="not a PlanetScope item metadata file"):
        product_planetscope.Product_Planetscope(str(bogus))


def test_item_without_asset_xml_is_rejected(tmp_path):
    item = tmp_path / "item"
    item.mkdir()
    for p in ORDER_DIR.glob(VO_ID + "_*"):
        if not p.name.endswith("_metadata.xml"):
            (item / p.name).write_bytes(p.read_bytes())
    with pytest.raises(Exception, match="no asset metadata XML"):
        product_planetscope.Product_Planetscope(str(item / VO_JSON.name))


def test_item_without_image_is_rejected(tmp_path):
    item = tmp_path / "item"
    item.mkdir()
    (item / VO_JSON.name).write_bytes(VO_JSON.read_bytes())
    with pytest.raises(Exception, match="no supported PlanetScope image asset"):
        product_planetscope.Product_Planetscope(str(item / VO_JSON.name))


def test_datetime_normalisation():
    norm = product_planetscope.normalise_utc
    assert norm("2021-03-14T07:08:03.311795Z") == "2021-03-14T07:08:03.311Z"
    assert norm("2017-04-24T13:49:11+00:00") == "2017-04-24T13:49:11.000Z"
    assert norm("2017-04-24T15:49:11.5+02:00") == "2017-04-24T13:49:11.500Z"
    assert norm(None) is None


def test_packager_selects_the_same_item_files():
    import importlib
    packager = importlib.import_module("planetscope_json.package_planetscope_zips")
    for item_id in (VO_ID, SR_ID):
        prod = product_planetscope.Product_Planetscope(str(ORDER_DIR / ("%s_metadata.json" % item_id)))
        assert [str(p) for p in packager.item_files(ORDER_DIR, item_id)] == prod.files


def test_sar_fields_and_other_missions_absent(work):
    _, _, feature = _feature(VO_JSON, VO_EO_NAME, work)
    paths = _key_paths(feature)
    for key in SAR_KEYS:
        assert not any(key in p for p in paths), "SAR field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OTHER_MISSION_TOKENS:
        assert tok not in blob, "other-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path, work):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(VO_JSON, work)
    json_emitter.emit(met, prod, VO_EO_NAME, str(out), native_product_name=VO_JSON.name)
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % VO_EO_NAME], written
