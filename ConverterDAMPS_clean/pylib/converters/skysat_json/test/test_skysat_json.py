"""Structural proof: drive skysat_json extraction on SYNTHETIC native SkySat
items, emit the JSON manifest via the common template generator, and assert
the output matches TDS/template/SSC-template.json key-path for key-path -
optical fields present, SAR fields absent, no placeholder left.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): no real
SkySat TDS product has been run yet. The pansharpened and L1A items carry the
values of the specialization's own example manifests.
"""
import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from skysat_json import product_skysat, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_ssc"
ORDER_DIR = FIXTURE_DIR / "order_5f3a" / "SkySatScene"
PSH_ID = "20180428_125611_ssc3d2_0017"
PSH_JSON = ORDER_DIR / ("%s_metadata.json" % PSH_ID)
PAN_ID = "20190612_101530_ssc7d3_0042"
PAN_JSON = ORDER_DIR / ("%s_metadata.json" % PAN_ID)
MSP_ID = "20160501_144606_ssc1d1_0005"
MSP_JSON = FIXTURE_DIR / MSP_ID / ("%s_metadata.json" % MSP_ID)
L1A_ID = "20160501_144606_ssc1d1_0006"
L1A_JSON = FIXTURE_DIR / L1A_ID / ("%s_metadata.json" % L1A_ID)
BDL_ID = "20200619_094518_ssc11_u0001"
BDL_JSON = FIXTURE_DIR / "collect" / BDL_ID / ("%s_metadata.json" % BDL_ID)
SSC_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "SSC-template.json"

# EO product names as the naming convention builds them
# (<MMM>_<CCCC>_<TTTTTTTTTT>_<start>_<stop>_<bbvv>)
PSH_EO_NAME = "SSC_OPER_L3_ORT_PSH_20180428T125611_20180428T125611_0001"
PAN_EO_NAME = "SSC_OPER_L3_ORT_PAN_20190612T101530_20190612T101530_0001"
MSP_EO_NAME = "SSC_OPER_L1BBDN_MSP_20160501T144606_20160501T144606_0001"
L1A_EO_NAME = "SSC_OPER_L1ABDN_PAN_20160501T144606_20160501T144606_0001"
BDL_EO_NAME = "SSC_OPER_SYNORT_BDL_20200619T094518_20200619T094518_0001"

# the eight product types the specialization allows (Tables 1, 2 and 3)
ALLOWED_PRODUCT_TYPES = {"L1ABDN_PAN", "L1BBDN_MS_", "L1BBDN_MSP", "L3_ORTVMS_",
                         "L3_ORT_PSH", "L3_ORT_MS_", "L3_ORT_PAN", "SYNORT_BDL"}

VNIR = {"spectralRange": "VNIR", "startWavelength": 450e-9, "endWavelength": 900e-9,
        "discreteWavelengths": [675e-9]}
VIS = {"spectralRange": "VIS", "startWavelength": 450e-9, "endWavelength": 695e-9,
       "discreteWavelengths": [482.5e-9, 555e-9, 650e-9]}
NIR = {"spectralRange": "NIR", "startWavelength": 740e-9, "endWavelength": 900e-9,
       "discreteWavelengths": [820e-9]}

SAR_KEYS = ["polarisationMode", "polarisationChannel", "rangeResolution",
            "azimuthResolution", "antennaLookDirection", "orbitNumber"]
OTHER_MISSION_TOKENS = ["GeoEye", "WorldView", "QuickBird", "Pleiades", "ICEYE",
                        "COSMO", "RADAR", "PlanetScope", "Dove"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(entry, work_folder):
    prod = product_skysat.Product_Skysat(str(entry))
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


def _copy_item(item_id, src_dir, dest_dir, keep):
    """Copy the item metadata and the files whose name contains one of keep."""
    dest_dir.mkdir()
    for p in src_dir.rglob(item_id + "_*"):
        if p.name.endswith("_metadata.json") or any(k in p.name for k in keep):
            shutil.copy(p, dest_dir / p.name)
    return dest_dir / ("%s_metadata.json" % item_id)


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def test_emitted_json_matches_ssc_template_structure(work):
    _, _, feature = _feature(PSH_JSON, PSH_EO_NAME, work)
    json_template.validate(feature)
    with open(SSC_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_pansharpened_scene_values(work):
    prod, _, feature = _feature(PSH_JSON, PSH_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    params = acq["acquisitionParameters"]
    assert feature["type"] == "Feature"
    assert feature["id"] == PSH_EO_NAME
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert len(ring) == 5 and ring[0] == ring[-1]
    assert ring[0] == [-66.44291264, -24.15261009]
    assert props["status"] == "ACQUIRED"
    assert props["title"] == PSH_EO_NAME
    assert props["date"] == "2018-04-28T12:56:11.806Z/2018-04-28T12:56:11.806Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "SkySat", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "SkySat Camera", "sensorType": "OPTICAL"}
    assert len(params) == 1
    par = params[0]
    assert par["beginningDateTime"] == par["endingDateTime"] == "2018-04-28T12:56:11.806Z"
    assert par["acquisitionType"] == "NOMINAL"
    assert par["operationalMode"] == "MS"
    assert par["resolution"] == 0.5
    assert par["wavelengths"] == [VNIR, VIS, NIR]
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "acrossTrackIncidenceAngle": 0.7}

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_ORT_PSH"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["processingDate"] == "2018-04-29T02:10:33.000Z"
    assert pinfo["cloudCover"] == 56.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"
    # only this item's files, not the other item sharing the folder
    assert pinfo["size"] == sum(p.stat().st_size for p in ORDER_DIR.glob(PSH_ID + "_*"))
    assert len(prod.files) == 4

    steps = pinfo["resourceLineage"][0]["processStep"]
    assert len(steps) == 1
    step = steps[0]
    assert step["description"] == "EOPF-EOS Converter for SkySat"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for SkySat products",
                                  "edition": "1.01"}]
    assert step["source"] == [{"sourceCitation": {"title": PSH_JSON.name},
                               "processedLevel": {"code": "L3B"}}]
    assert step["processingInformation"]["softwareReference"]["title"] == \
        "EOPF-EOS Converter for SkySat"
    assert step["output"] == [{"sourceCitation": {"title": "%s.ZIP" % PSH_EO_NAME}}]

    links = props["links"]
    assert links["measurements"] == [{"href": "/measurements/%s_pansharpened.tif" % PSH_ID,
                                      "type": "image/tiff", "title": "Native EO Product",
                                      "category": "DATA"}]
    assert links["previews"] == [{"href": "/previews/overviews/%s.PNG" % PSH_EO_NAME,
                                 "type": "image/png", "title": "Preview Image",
                                 "category": "OVERVIEW"}]


def test_visual_asset_is_the_ortho_scene_overview_source():
    prod = product_skysat.Product_Skysat(str(PSH_JSON))
    assert prod.components[0]["file"].endswith("_pansharpened.tif")
    assert prod.components[0]["overview"].endswith("_visual.tif")


def test_ortho_panchromatic_scene(work):
    _, _, feature = _feature(PAN_JSON, PAN_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "PAN"
    assert par["wavelengths"] == [VNIR]
    assert par["acquisitionAngles"]["acrossTrackIncidenceAngle"] == 12.4
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_ORT_PAN"
    assert pinfo["cloudCover"] == 3.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32632"
    assert props["links"]["measurements"][0]["href"] == \
        "/measurements/%s_panchromatic_dn.tif" % PAN_ID


def test_basic_panchromatic_multispectral_scene(work):
    """Legacy per-asset sub-folders, level 1B, two measurements, no CRS, no
    cloud cover, gsd as resolution, clockwise footprint turned
    counter-clockwise."""
    prod, _, feature = _feature(MSP_JSON, MSP_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "MS"
    assert par["wavelengths"] == [VNIR, VIS, NIR]
    assert par["resolution"] == 0.86  # no pixel_resolution: gsd

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1BBDN_MSP"
    assert pinfo["processingLevel"] == "1B"
    assert "referenceSystemIdentifier" not in pinfo
    assert "cloudCover" not in pinfo
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1B"

    ring = feature["geometry"]["coordinates"][0]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    assert area > 0, "footprint must be counter-clockwise (RFC 7946)"
    assert [m["href"] for m in props["links"]["measurements"]] == [
        "/measurements/basic_panchromatic_dn/%s_basic_panchromatic_dn.tif" % MSP_ID,
        "/measurements/basic_analytic_dn/%s_basic_analytic_dn.tif" % MSP_ID]
    assert len(props["links"]["previews"]) == 1
    assert len(prod.files) == 5  # json + 2 tif + 2 rpc


def test_basic_l1a_panchromatic_scene(work):
    """Values of the specialization's L1ABDN_PAN example manifest."""
    _, _, feature = _feature(L1A_JSON, L1A_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "PAN"
    assert par["resolution"] == 0.5
    assert par["wavelengths"] == [VNIR]
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "acrossTrackIncidenceAngle": 35.1}
    assert props["date"] == "2016-05-01T14:46:06.806Z/2016-05-01T14:46:06.806Z"
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1ABDN_PAN"
    assert pinfo["processingLevel"] == "1A"
    assert pinfo["cloudCover"] == 56.0
    assert "referenceSystemIdentifier" not in pinfo
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1A"
    assert feature["geometry"]["coordinates"][0][0] == [-66.44291264, -24.15261009]


def test_bundle_collect(work):
    _, _, feature = _feature(BDL_JSON, BDL_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    params = props["acquisitionInformation"][0]["acquisitionParameters"]
    # spec Table 3 / Table 16, in the example's order
    assert [p["operationalMode"] for p in params] == ["MS", "MS", "MS4B", "PAN"]
    assert [p["wavelengths"] for p in params] == [[VNIR, VIS], [VNIR, VIS, NIR], [VIS, NIR], [VNIR]]
    for p in params:
        assert p["beginningDateTime"] == "2020-06-19T09:45:18.250Z"
        assert p["resolution"] == 0.5
        assert p["acquisitionAngles"]["acrossTrackIncidenceAngle"] == 0.7

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "SYNORT_BDL"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["cloudCover"] == 5.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32633"
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "SYN"

    links = props["links"]
    assert [m["href"] for m in links["measurements"]] == [
        "/measurements/%s_%s.tif" % (BDL_ID, kind)
        for kind in ("visual", "pansharpened", "analytic", "panchromatic")]
    assert [p["href"] for p in links["previews"]] == [
        "/previews/overviews/%s_%s.PNG" % (BDL_EO_NAME, s) for s in ("PSH3B", "PSH4B", "MS", "PAN")]

    # MultiPolygon -> bounding box of all rings, as a Polygon
    assert feature["geometry"] == {"type": "Polygon", "coordinates": [[
        [15.0, 40.0], [15.3, 40.0], [15.3, 40.2], [15.0, 40.2], [15.0, 40.0]]]}


def test_bundle_with_missing_components(tmp_path, work):
    entry = _copy_item(BDL_ID, BDL_JSON.parent, tmp_path / "item", ("_analytic", "_panchromatic"))
    _, _, feature = _feature(entry, BDL_EO_NAME, work)
    params = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert [p["operationalMode"] for p in params] == ["MS4B", "PAN"]
    assert [p["href"][-7:] for p in feature["properties"]["links"]["previews"]] == ["_MS.PNG", "PAN.PNG"]


@pytest.mark.parametrize("keep,typecode,mode,wavelengths", [
    (("_visual",), "L3_ORTVMS_", "MS", [VIS]),
    (("_analytic_dn",), "L3_ORT_MS_", "MS", [VIS, NIR]),
])
def test_other_ortho_scene_types(tmp_path, work, keep, typecode, mode, wavelengths):
    src = BDL_JSON.parent
    item = tmp_path / "item"
    item.mkdir()
    # a SkySatScene item rebuilt from the collect rasters
    scene_id = "20200619_094518_ssc11d1_0003"
    feature = json.loads(BDL_JSON.read_text(encoding="utf-8"))
    feature["id"] = scene_id
    feature["properties"]["item_type"] = "SkySatScene"
    (item / ("%s_metadata.json" % scene_id)).write_text(json.dumps(feature), encoding="utf-8")
    for k in keep:
        name = k.replace("_dn", "")
        shutil.copy(src / ("%s%s.tif" % (BDL_ID, name)), item / ("%s%s.tif" % (scene_id, k)))
    _, _, out = _feature(item / ("%s_metadata.json" % scene_id), PSH_EO_NAME, work)
    assert json_template.find_placeholders(out) == []
    par = out["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert out["properties"]["productInformation"]["productType"] == typecode
    assert par["operationalMode"] == mode
    assert par["wavelengths"] == wavelengths


def test_basic_multispectral_scene(tmp_path, work):
    entry = _copy_item(MSP_ID, MSP_JSON.parent, tmp_path / "item", ("_basic_analytic_dn",))
    _, _, feature = _feature(entry, MSP_EO_NAME, work)
    par = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert feature["properties"]["productInformation"]["productType"] == "L1BBDN_MS_"
    assert par["operationalMode"] == "MS4B"
    assert par["wavelengths"] == [VIS, NIR]
    assert [m["href"] for m in feature["properties"]["links"]["measurements"]] == [
        "/measurements/%s_basic_analytic_dn.tif" % MSP_ID]


def test_lineage_citation_is_the_entry_file(work):
    """The runner and the packager find the native item back from it."""
    _, _, feature = _feature(BDL_JSON, BDL_EO_NAME, work)
    assert json_template.lineage_citation(feature) == BDL_JSON.name


@pytest.mark.parametrize("entry", [PSH_JSON, PAN_JSON, MSP_JSON, L1A_JSON, BDL_JSON])
def test_overview_pngs(tmp_path, entry):
    prod = product_skysat.Product_Skysat(str(entry))
    paths = prod.writeQuicklooks(str(tmp_path), "SSC_TEST")
    assert [os.path.basename(p) for p in paths] == prod.overview_names("SSC_TEST")

    from PIL import Image
    for png in paths:
        with Image.open(png) as im:
            assert im.format == "PNG"
            assert im.mode == "RGBA"
            assert im.size == (16, 12)
            # the zero (no-data) first column is transparent, the rest opaque
            assert im.getpixel((0, 5))[3] == 0
            assert im.getpixel((8, 5))[3] == 255


def test_panchromatic_overview_is_grey(tmp_path):
    prod = product_skysat.Product_Skysat(str(PAN_JSON))
    png = prod.writeQuicklooks(str(tmp_path), "SSC_TEST")[0]
    from PIL import Image
    with Image.open(png) as im:
        r, g, b, _ = im.getpixel((8, 5))
        assert r == g == b


def test_product_type_tables_are_the_specialization_ones():
    scene_types = {row[1] for row in product_skysat.SCENE_ASSETS}
    assert scene_types | {product_skysat.BUNDLE_TYPECODE} == ALLOWED_PRODUCT_TYPES
    assert set(product_skysat.PRODUCT_TYPES) == scene_types
    for typecode in ALLOWED_PRODUCT_TYPES:
        assert len(typecode) == 10, typecode
    for _, typecode, level, kind in product_skysat.SCENE_ASSETS:
        assert level in product_skysat.PROCESSING_LEVEL
        assert kind in product_skysat.IMAGE_KINDS
        assert product_skysat.PRODUCT_TYPES[typecode][0] in product_skysat.OPERATIONAL_MODES
    for kind, suffix, patterns, mode, ranges in product_skysat.BUNDLE_COMPONENTS:
        assert kind in product_skysat.IMAGE_KINDS
        assert mode in product_skysat.OPERATIONAL_MODES
    # band count of the spectral ranges = band count of the image kind,
    # panchromatic aside (one VNIR band over the whole range)
    for kind, suffix, patterns, mode, ranges in product_skysat.BUNDLE_COMPONENTS:
        bands = sum(len(product_skysat.SPECTRAL_RANGES[r]) for r in ranges if r != 'VNIR')
        assert bands in (0, product_skysat.IMAGE_KINDS[kind][0]), kind


def test_entry_must_be_item_metadata(tmp_path):
    bogus = tmp_path / "manifest.json"
    bogus.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception, match="not a SkySat item metadata file"):
        product_skysat.Product_Skysat(str(bogus))


def test_planetscope_item_is_rejected(tmp_path):
    item = tmp_path / "x_metadata.json"
    item.write_text(json.dumps({"type": "Feature", "properties": {"item_type": "PSScene"}}),
                    encoding="utf-8")
    with pytest.raises(Exception, match="unsupported SkySat item_type"):
        product_skysat.Product_Skysat(str(item))


def test_item_without_image_is_rejected(tmp_path):
    item = tmp_path / "item"
    item.mkdir()
    (item / PSH_JSON.name).write_bytes(PSH_JSON.read_bytes())
    with pytest.raises(Exception, match="no supported SkySat scene image asset"):
        product_skysat.Product_Skysat(str(item / PSH_JSON.name))


def test_datetime_normalisation():
    norm = product_skysat.normalise_utc
    assert norm("2018-04-28T12:56:11.806371Z") == "2018-04-28T12:56:11.806Z"
    assert norm("2016-05-01T20:00:00Z") == "2016-05-01T20:00:00.000Z"
    assert norm("2017-04-24T15:49:11.5+02:00") == "2017-04-24T13:49:11.500Z"
    assert norm(None) is None


def test_packager_selects_the_same_item_files():
    import importlib
    packager = importlib.import_module("skysat_json.package_skysat_zips")
    for item_id in (PSH_ID, PAN_ID):
        prod = product_skysat.Product_Skysat(str(ORDER_DIR / ("%s_metadata.json" % item_id)))
        assert [str(p) for p in packager.item_files(ORDER_DIR, item_id)] == prod.files


def test_packager_builds_the_bundle_zip(tmp_path, work, monkeypatch):
    import importlib
    packager = importlib.import_module("skysat_json.package_skysat_zips")
    outspace, products = tmp_path / "OUTSPACE", tmp_path / "PRODUCTS"
    outspace.mkdir()
    products.mkdir()
    prod, met = _extract(BDL_JSON, work)
    json_emitter.emit(met, prod, BDL_EO_NAME, str(outspace), native_product_name=BDL_JSON.name)
    prod.writeQuicklooks(str(outspace), BDL_EO_NAME)

    spaces = dict(packager.SPACES, INBOX=FIXTURE_DIR, OUTSPACE=outspace, PRODUCTS=products,
                  TMPSPACE=tmp_path / "none", DONESPACE=tmp_path / "none")
    monkeypatch.setattr(packager, "SPACES", spaces)
    monkeypatch.setattr(packager, "OUTSPACE", outspace)
    monkeypatch.setattr(packager, "PRODUCTS", products)
    native = packager.package_one(outspace / ("%s.JSON" % BDL_EO_NAME))
    assert native == BDL_JSON.parent

    with zipfile.ZipFile(products / ("%s.ZIP" % BDL_EO_NAME)) as zf:
        names = set(zf.namelist())
        assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())
    assert "%s.JSON" % BDL_EO_NAME in names
    assert {"previews/overviews/%s_%s.PNG" % (BDL_EO_NAME, s)
            for s in ("PSH3B", "PSH4B", "MS", "PAN")} <= names
    assert {"measurements/%s" % p.name for p in BDL_JSON.parent.iterdir()} <= names
    assert len(names) == 1 + 4 + 6


def test_sar_fields_and_other_missions_absent(work):
    _, _, feature = _feature(BDL_JSON, BDL_EO_NAME, work)
    paths = _key_paths(feature)
    for key in SAR_KEYS:
        assert not any(key in p for p in paths), "SAR field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OTHER_MISSION_TOKENS:
        assert tok not in blob, "other-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path, work):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(PSH_JSON, work)
    json_emitter.emit(met, prod, PSH_EO_NAME, str(out), native_product_name=PSH_JSON.name)
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % PSH_EO_NAME], written
