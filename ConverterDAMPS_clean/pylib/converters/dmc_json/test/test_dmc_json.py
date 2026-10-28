"""Tests for dmc_json: the DIMAP reader, the delivery rules, the package
names, the packager and the manifest.

Native products are the SYNTHETIC deliveries of fixtures/synthetic_dmc (see
fixtures/SYNTHETIC_FIXTURE_NOTE.md): the file set and element paths of the
real Beijing-1 L1R / L1T deliveries, synthetic values. Failing products are edited
copies. Manifest tests against TDS/template/DMC-template.json (the spec
section 6.1 example) fill the metadata by hand.

TODO(DMC-PENDING:NATIVE-META): add NigeriaSat-1 / UK-DMC-1 products
once their samples exist.
"""
import configparser
import json
import re
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

from eoSip_converter.esaProducts import metadata as M
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes
from common import json_template, spaces
from dmc_json import json_emitter as E
from dmc_json import name_registry as NR
from dmc_json import package_dmc_zips as PKG
from dmc_json import product_dmc as P

HERE = Path(__file__).resolve().parent
SYNTHETIC = HERE / "fixtures" / "synthetic_dmc"
CFG = HERE.parent / "ingest_dmc.cfg"
# fixture folders (short names: Windows path limit); the dataset names are
# the DATASET_NAME inside each .dim
REF = "l1r_p"
SIDE = "l1r_s"
L1T = "l1t_p"
L1T_QL = "l1t_ql"
REF_DATASET = "DS00001a_000000_010499_p_L1R_AA"
SIDE_DATASET = "DS00001a_000000_010499_s_L1R_BB"
REF_EO_NAME = "BJ1_OPER_L1_OPT_MS__20090210T101112_20090210T101112_0001"
SIDE_EO_NAME = "BJ1_OPER_L1_OPT_MS__20090210T101112_20090210T101112_0002"
L1T_EO_NAME = "BJ1_OPER_L1_ORT_MS__20090506T070809_20090506T070809_0001"
L1T_QL_EO_NAME = "BJ1_OPER_L1_ORT_MS__20090506T070809_20090506T070809_0002"


def copy_product(name, dest):
    """Copy a synthetic delivery folder under dest; returns its .dim."""
    shutil.copytree(SYNTHETIC / name, dest / name)
    return dest / name / (name + ".dim")


def edit_dim(dim, old, new):
    text = dim.read_text(encoding="ISO-8859-1")
    assert old in text
    dim.write_text(text.replace(old, new), encoding="ISO-8859-1")


def edit_repository(dim, old, new):
    sip = dim.with_name(dim.stem + P.SIP_SUFFIX)
    with zipfile.ZipFile(sip) as zf:
        entries = {n: zf.read(n) for n in zf.namelist()}
    text = entries[P.REPOSITORY_XML].decode("ISO-8859-1")
    assert old in text
    entries[P.REPOSITORY_XML] = text.replace(old, new).encode("ISO-8859-1")
    with zipfile.ZipFile(sip, "w") as zf:
        for n, data in entries.items():
            zf.writestr(n, data)


def mission_values():
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(CFG)
    return dict(cfg.items("Mission-specific-values")), cfg.get("Output", "OUTPUT_EO_PATTERN")


def extract(dim, work):
    prod = P.Product_DMC(str(dim))
    prod.setDebug(0)
    prod.extractToPath(str(work))
    met = M.Metadata(mission_values()[0])
    prod.extractMetadata(met)
    return prod, met


def eo_name(prod, met, registry):
    """Package name as the ingester builds it: counter from the registry,
    then the naming convention."""
    pattern = mission_values()[1]
    NR.assign_version(met, prod.dataset_name, pattern, registry_path=str(registry))
    return NamingConvention_HightRes(pattern).buildProductName(met, None)


def name_of(name, tmp_path, work, registry):
    prod, met = extract(copy_product(name, tmp_path), work)
    return eo_name(prod, met, registry)


def feature_of(dim, work, registry=None):
    prod, met = extract(dim, work)
    name = eo_name(prod, met, registry or work / "dmc_names.json")
    # the ingester passes the entry file's basename, as here
    feature = json_template.build(*E.build_layers(met, prod, name, native_product_name=dim.name),
                                  template_path=E.TEMPLATE_PATH)
    json_template.validate(feature)
    return feature


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


# -- spec lookup tables -------------------------------------------------------

def test_platform_table_is_the_specification_one():
    # spec Tables 1 and 8
    assert P.PLATFORMS == {
        "BJ1": ("BJ", "1", "Beijing-1"),
        "NG1": ("NG", "1", "NigeriaSat-1"),
        "UK1": ("UK", "1", "UK-DMC-1"),
    }
    assert set(P.NATIVE_PLATFORMS.values()) <= set(P.PLATFORMS)


def test_product_type_table_is_the_specification_one():
    # spec Table 2 product types, Table 17 processedLevel codes
    assert P.PRODUCT_TYPES == {"L1R": "L1_OPT_MS_", "L1T": "L1_ORT_MS_"}
    assert all(len(t) == 10 for t in P.PRODUCT_TYPES.values())
    assert set(P.NATIVE_LEVELS.values()) <= set(P.PRODUCT_TYPES)
    assert (P.INSTRUMENT, P.OPERATIONAL_MODE, P.PROCESSING_LEVEL) == ("SLIM6", "MS3B", "1")


def test_wavelengths_follow_table_14():
    got = P.wavelengths()
    assert got == [
        {"spectralRange": "VIS", "startWavelength": 520e-9, "endWavelength": 690e-9,
         "discreteWavelengths": [560e-9, 660e-9]},
        {"spectralRange": "NIR", "startWavelength": 770e-9, "endWavelength": 900e-9,
         "discreteWavelengths": [835e-9]},
    ]


# -- helpers ------------------------------------------------------------------

def test_format_utc_is_rfc3339_with_milliseconds():
    assert P.format_utc(datetime(2007, 8, 28, 8, 6, 43, 806500, tzinfo=timezone.utc)) \
        == "2007-08-28T08:06:43.806Z"
    assert P.format_utc(datetime(2007, 8, 28, 10, 6, 43, tzinfo=timezone(timedelta(hours=2)))) \
        == "2007-08-28T08:06:43.000Z"
    # naive datetimes are taken as UTC
    assert P.format_utc(datetime(2007, 8, 28, 8, 6, 43)) == "2007-08-28T08:06:43.000Z"


def test_dim_datetime_is_taken_as_utc():
    assert P.format_utc(P.parse_dim_datetime("2007-08-08 08:23:21")) == "2007-08-08T08:23:21.000Z"


def test_crs_uri():
    assert P.crs_uri("32614") == "http://www.opengis.net/def/crs/EPSG/0/32614"
    assert P.crs_uri(4326) == "http://www.opengis.net/def/crs/EPSG/0/4326"
    with pytest.raises(Exception):
        P.crs_uri(0)
    with pytest.raises(Exception):
        P.crs_uri("CUSTOM:50008")


def test_footprint_ring_is_closed_and_counter_clockwise():
    clockwise = [(0, 0), (0, 1), (1, 1), (1, 0)]
    ring = P.closed_ccw_ring(clockwise)
    assert ring[0] == ring[-1] and len(ring) == 5
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    assert area > 0
    # an already closed counter-clockwise ring is kept as is
    assert P.closed_ccw_ring(ring) == ring
    with pytest.raises(Exception):
        P.closed_ccw_ring([(0, 0), (1, 1)])
    with pytest.raises(Exception):
        P.closed_ccw_ring([(0, 0), (1, 1), (2, 2)])


# -- package name counter (name_registry) -------------------------------------

def test_registry_counts_first_come_first_served(tmp_path):
    path = tmp_path / "dmc_names.json"
    base = lambda v: "BASE_" + v
    reg = NR.NameRegistry(str(path))
    assert reg.version_for("A", base) == "0001"
    assert reg.version_for("B", base) == "0002"
    # a native product converted again gets its own name back
    assert reg.version_for("A", base) == "0001"
    # another name starts again from 01
    assert reg.version_for("C", lambda v: "OTHER_" + v) == "0001"
    # the registry is kept on disk: a later run continues from it
    assert NR.NameRegistry(str(path)).version_for("D", base) == "0003"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "A": "BASE_0001", "B": "BASE_0002", "C": "OTHER_0001", "D": "BASE_0003"}


def test_registry_counter_limit(tmp_path):
    path = tmp_path / "dmc_names.json"
    path.write_text(json.dumps({"N%d" % c: "BASE_00%02d" % c for c in range(1, 100)}),
                    encoding="utf-8")
    with pytest.raises(Exception, match="counter limit 99"):
        NR.NameRegistry(str(path)).version_for("NEW", lambda v: "BASE_" + v)


def test_registry_refuses_a_changed_name(tmp_path):
    path = tmp_path / "dmc_names.json"
    path.write_text(json.dumps({"A": "BASE_0001"}), encoding="utf-8")
    with pytest.raises(Exception, match="metadata changed"):
        NR.NameRegistry(str(path)).version_for("A", lambda v: "NEW_" + v)


def test_registry_refuses_an_unreadable_file(tmp_path):
    path = tmp_path / "dmc_names.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(Exception, match="not valid JSON"):
        NR.NameRegistry(str(path))


def test_registry_path_comes_from_the_cfg():
    assert mission_values()[0][NR.REGISTRY_KEY] == r"TDS\DMC\dmc_names.json"
    with pytest.raises(Exception, match=NR.REGISTRY_KEY):
        NR.assign_version(M.Metadata(None), "A", mission_values()[1])


def test_frame_points():
    import xml.etree.ElementTree as ET
    geographic = ET.fromstring(
        '<D><Dataset_Frame><Vertex><FRAME_X unit="DEG">1.5</FRAME_X>'
        '<FRAME_Y unit="DEG">2.5</FRAME_Y></Vertex></Dataset_Frame></D>')
    assert P.frame_points(geographic) == [("1.5", "2.5")]
    projected = ET.fromstring(
        '<D><Dataset_Frame><Vertex><FRAME_LON unit="DEG">1.5</FRAME_LON>'
        '<FRAME_LAT unit="DEG">2.5</FRAME_LAT><FRAME_X unit="M">3000.0</FRAME_X>'
        '<FRAME_Y unit="M">7000.0</FRAME_Y></Vertex></Dataset_Frame></D>')
    assert P.frame_points(projected) == [("1.5", "2.5")]
    metres_only = ET.fromstring(
        '<D><Dataset_Frame><Vertex><FRAME_X unit="M">3000.0</FRAME_X>'
        '<FRAME_Y unit="M">7000.0</FRAME_Y></Vertex></Dataset_Frame></D>')
    with pytest.raises(Exception, match="without degrees"):
        P.frame_points(metres_only)


# -- product: delivery rules ----------------------------------------------------

def test_entry_must_be_a_dim(tmp_path):
    dim = copy_product(REF, tmp_path)
    with pytest.raises(Exception, match="DIMAP header"):
        P.Product_DMC(str(dim.with_suffix(".htm")))


def test_delivery_folder_quicklook_and_size(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    prod = P.Product_DMC(str(dim))
    prod.extractToPath(str(work))
    assert Path(prod.EO_FOLDER) == dim.parent
    assert prod.dim_name == dim.name
    assert Path(prod.browse_path).name == REF + "_ql.jpg"
    # size: the whole delivery, .tif / .htm / .xsl / _meta.sip included
    assert prod.tmpSize == sum(p.stat().st_size for p in dim.parent.iterdir())
    assert sorted(prod.contentList) == sorted(p.name for p in dim.parent.iterdir())


def test_missing_quicklook_fails(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    (dim.parent / (REF + "_ql.jpg")).unlink()
    prod = P.Product_DMC(str(dim))
    with pytest.raises(Exception, match="quicklook"):
        prod.extractToPath(str(work))


def test_setters(tmp_path):
    dim = copy_product(REF, tmp_path)
    prod = P.Product_DMC(str(dim))
    prod.metadata = M.Metadata(None)
    prod.set_platform("BJ1")
    prod.set_level("L1R")
    met = prod.metadata
    assert met.getMetadataValue(M.METADATA_PLATFORM_2DIGITS_ALIAS) == "BJ"
    assert met.getMetadataValue(M.METADATA_PLATFORM_ID) == "1"
    assert met.getMetadataValue(M.METADATA_PLATFORM) == "Beijing-1"
    assert met.getMetadataValue(M.METADATA_INSTRUMENT) == "SLIM6"
    assert met.getMetadataValue(M.METADATA_TYPECODE) == "L1_OPT_MS_"
    assert met.getMetadataValue(M.METADATA_PROCESSING_LEVEL) == "1"
    assert met.getMetadataValue(P.PROCESSED_LEVEL_CODE) == "L1R"
    assert met.getMetadataValue(M.METADATA_SENSOR_OPERATIONAL_MODE) == "MS3B"
    with pytest.raises(Exception):
        prod.set_platform("DM1")
    with pytest.raises(Exception):
        prod.set_level("L0R")


# -- product: metadata reader ------------------------------------------------------

def test_reference_product_values(tmp_path, work):
    prod, met = extract(copy_product(REF, tmp_path), work)
    g = met.getMetadataValue
    assert (g(M.METADATA_PLATFORM), g(M.METADATA_PLATFORM_ID)) == ("Beijing-1", "1")
    assert (g(M.METADATA_TYPECODE), g(P.PROCESSED_LEVEL_CODE)) == ("L1_OPT_MS_", "L1R")
    # the registry key; the counter itself is not read from the .dim
    assert prod.dataset_name == REF_DATASET
    # scene centre time only: beginning = ending (spec Table 11)
    assert g(M.METADATA_START_DATE_TIME) == g(M.METADATA_STOP_DATE_TIME) == "2009-02-10T10:11:12.000Z"
    assert (g(M.METADATA_START_DATE), g(M.METADATA_START_TIME)) == ("2009-02-10", "10:11:12.000")
    assert (g(M.METADATA_SUN_AZIMUTH), g(M.METADATA_SUN_ELEVATION)) == (140.5, 35.25)
    assert g(M.METADATA_RESOLUTION) == 32.5
    assert g(M.METADATA_PROCESSING_TIME) == "2009-03-02T00:00:00.000Z"
    assert met.getLocalAttributeValue("referenceSystemIdentifier") == \
        "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert met.getLocalAttributeValue("footprintRing") == \
        [[10.0, 50.0], [11.0, 47.0], [15.0, 47.5], [14.0, 50.5], [10.0, 50.0]]
    # no cloud cover, no incidence angles, no orbit in the delivery
    for key in (M.METADATA_CLOUD_COVERAGE, M.METADATA_ORBIT, M.METADATA_ORBIT_DIRECTION,
                M.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE,
                M.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE):
        assert not met.valueExists(g(key))


def test_side_product_values(tmp_path, work):
    prod, met = extract(copy_product(SIDE, tmp_path), work)
    assert prod.dataset_name == SIDE_DATASET
    assert met.getMetadataValue(M.METADATA_CLOUD_COVERAGE) == 12.5
    # clockwise frame turned counter-clockwise
    assert met.getLocalAttributeValue("footprintRing") == \
        [[6.0, 49.5], [7.0, 46.5], [11.0, 47.0], [10.0, 50.0], [6.0, 49.5]]


def test_p_and_s_products_of_one_scene_get_different_names(tmp_path, work):
    registry = tmp_path / "dmc_names.json"
    names = [name_of(n, tmp_path, work, registry) for n in (REF, SIDE)]
    assert names == [REF_EO_NAME, SIDE_EO_NAME]
    assert all(len(n) == 56 for n in names)
    # converted again: same names, nothing new in the registry
    shutil.rmtree(tmp_path / REF)
    assert name_of(REF, tmp_path, work, registry) == REF_EO_NAME
    assert len(json.loads(registry.read_text(encoding="utf-8"))) == 2


def test_counter_follows_the_processing_order(tmp_path, work):
    registry = tmp_path / "dmc_names.json"
    names = [name_of(n, tmp_path, work, registry) for n in (SIDE, REF)]
    assert names == [REF_EO_NAME, SIDE_EO_NAME]
    assert json.loads(registry.read_text(encoding="utf-8")) == {
        SIDE_DATASET: REF_EO_NAME, REF_DATASET: SIDE_EO_NAME}


def test_l1t_product_values(tmp_path, work):
    prod, met = extract(copy_product(L1T, tmp_path), work)
    g = met.getMetadataValue
    assert (g(M.METADATA_TYPECODE), g(P.PROCESSED_LEVEL_CODE)) == ("L1_ORT_MS_", "L1T")
    assert g(M.METADATA_RESOLUTION) == 21.9
    assert met.getLocalAttributeValue("referenceSystemIdentifier") == \
        "http://www.opengis.net/def/crs/EPSG/0/4258"
    assert met.getLocalAttributeValue("footprintRing") == \
        [[24.0, 68.0], [20.0, 67.5], [21.0, 66.0], [25.0, 66.5], [24.0, 68.0]]


def test_ql_product_is_a_normal_product(tmp_path, work):
    prod, met = extract(copy_product(L1T_QL, tmp_path), work)
    g = met.getMetadataValue
    assert (g(M.METADATA_TYPECODE), g(P.PROCESSED_LEVEL_CODE)) == ("L1_ORT_MS_", "L1T")
    assert g(M.METADATA_RESOLUTION) == 320.0
    # projected CRS: the footprint comes from FRAME_LON / FRAME_LAT, not the
    # FRAME_X / FRAME_Y metres
    assert met.getLocalAttributeValue("referenceSystemIdentifier") == \
        "http://www.opengis.net/def/crs/EPSG/0/2393"
    assert met.getLocalAttributeValue("footprintRing") == \
        [[24.0, 68.0], [20.0, 67.5], [21.0, 66.0], [25.0, 66.5], [24.0, 68.0]]


def test_l1t_product_and_its_ql_copy_get_different_names(tmp_path, work):
    registry = tmp_path / "dmc_names.json"
    names = [name_of(n, tmp_path, work, registry) for n in (L1T, L1T_QL)]
    assert names == [L1T_EO_NAME, L1T_QL_EO_NAME]


def test_frame_in_metres_only_fails(tmp_path, work):
    dim = copy_product(L1T_QL, tmp_path)
    text = dim.read_text(encoding="ISO-8859-1")
    text = re.sub(r"\s*<FRAME_(LON|LAT) [^>]*>[^<]*</FRAME_(LON|LAT)>", "", text)
    dim.write_text(text, encoding="ISO-8859-1")
    with pytest.raises(Exception, match="without degrees"):
        extract(dim, work)


def test_no_crs_is_left_out(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    edit_dim(dim, "<HORIZONTAL_CS_CODE>EPSG:4326</HORIZONTAL_CS_CODE>", "")
    prod, met = extract(dim, work)
    assert met.getLocalAttributeValue("referenceSystemIdentifier") is None


@pytest.mark.parametrize("old,new,message", [
    ("<MISSION>BEIJING</MISSION>", "<MISSION>UNKNOWN</MISSION>", "MISSION"),
    ("<INSTRUMENT>SLIM-6</INSTRUMENT>", "<INSTRUMENT>OTHER</INSTRUMENT>", "INSTRUMENT"),
    # a level code not in NATIVE_LEVELS
    ("<GEOMETRIC_PROCESSING>1R_AA</GEOMETRIC_PROCESSING>",
     "<GEOMETRIC_PROCESSING>9X_AA</GEOMETRIC_PROCESSING>", "GEOMETRIC_PROCESSING"),
    ("<DATASET_NAME>%s</DATASET_NAME>" % REF_DATASET, "", "DATASET_NAME"),
    ('<SUN_AZIMUTH unit="DEG">140.5</SUN_AZIMUTH>', "", "SUN_AZIMUTH"),
    ("<SCENE_CENTER_TIME>2009-02-10 10:11:12</SCENE_CENTER_TIME>", "", "SCENE_CENTER_TIME"),
])
def test_unsupported_or_missing_dim_values_fail(tmp_path, work, old, new, message):
    dim = copy_product(REF, tmp_path)
    edit_dim(dim, old, new)
    with pytest.raises(Exception, match=message):
        extract(dim, work)


def test_missing_meta_sip_fails(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    dim.with_name(REF + P.SIP_SUFFIX).unlink()
    with pytest.raises(Exception, match="_meta.sip"):
        extract(dim, work)


def test_missing_resolution_fails(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    edit_repository(dim, "<Resolution>32.5</Resolution>", "<Resolution></Resolution>")
    with pytest.raises(Exception, match="Resolution"):
        extract(dim, work)


def test_folder_of_zips_has_no_entry(tmp_path):
    # a nested delivery (a zip of zips) unpacks to a folder of zips: no .dim
    # is found, so nothing is converted
    stage = tmp_path / "TMPSPACE" / "STAGE_nested" / "nested"
    stage.mkdir(parents=True)
    for name in (REF, SIDE):
        with zipfile.ZipFile(stage / (name + ".zip"), "w") as zf:
            for p in (SYNTHETIC / name).iterdir():
                zf.write(p, p.name)
    sp = dict(spaces.read_spaces(CFG), INBOX=tmp_path / "INBOX", TMPSPACE=tmp_path / "TMPSPACE",
              DONESPACE=tmp_path / "DONESPACE")
    assert spaces.find_entries(sp) == []


# -- packager -------------------------------------------------------------------

@pytest.fixture
def spaces_in(tmp_path, monkeypatch):
    sp = {k: tmp_path / k for k in ("INBOX", "TMPSPACE", "OUTSPACE", "DONESPACE", "PRODUCTS")}
    for p in sp.values():
        p.mkdir()
    monkeypatch.setattr(PKG, "SPACES", dict(PKG.SPACES, **sp))
    monkeypatch.setattr(PKG, "OUTSPACE", sp["OUTSPACE"])
    monkeypatch.setattr(PKG, "PRODUCTS", sp["PRODUCTS"])
    return sp


def write_manifest(feature, out_dir):
    mf = out_dir / ("%s.JSON" % feature["id"])
    mf.write_text(json.dumps(feature, indent=2), encoding="utf-8")
    return mf


def test_packager_builds_the_delivery_zip(spaces_in, work):
    dim = copy_product(REF, spaces_in["INBOX"])
    # a second JPEG next to the quicklook: the one the .dim names is used
    Image.new("RGB", (16, 12), (255, 255, 255)).save(dim.parent / "other.jpg", "JPEG")
    feature = feature_of(dim, work)
    mf = write_manifest(feature, spaces_in["OUTSPACE"])
    native = dim.parent
    assert PKG.package_one(mf) == native

    with zipfile.ZipFile(spaces_in["PRODUCTS"] / ("%s.ZIP" % REF_EO_NAME)) as zf:
        assert {i.compress_type for i in zf.infolist()} == {zipfile.ZIP_STORED}
        assert zf.read("%s.JSON" % REF_EO_NAME) == mf.read_bytes()
        png = "previews/overviews/%s.PNG" % REF_EO_NAME
        measurements = {"measurements/%s" % p.name for p in native.iterdir()}
        assert set(zf.namelist()) == measurements | {"%s.JSON" % REF_EO_NAME, png}
        assert "measurements/%s" % dim.name in measurements
        with Image.open(zf.open(png)) as im:
            assert im.format == "PNG"
            # the green quicklook, not the white other.jpg
            r, g, b = im.convert("RGB").getpixel((8, 6))
            assert g > 150 and r < 80 and b < 80


def test_packager_and_converter_pick_the_same_quicklook(tmp_path):
    dim = copy_product(SIDE, tmp_path)
    assert Path(P.dim_quicklook(str(dim))) == PKG.dim_quicklook(dim)


def test_packager_rejects_a_measurements_href_outside_the_delivery(spaces_in, work):
    dim = copy_product(REF, spaces_in["INBOX"])
    feature = feature_of(dim, work)
    feature["properties"]["links"]["measurements"][0]["href"] = "/measurements/missing.tif"
    with pytest.raises(Exception, match="not in the delivery"):
        PKG.package_one(write_manifest(feature, spaces_in["OUTSPACE"]))


def test_packager_rejects_a_citation_that_is_not_a_dim(spaces_in, work):
    dim = copy_product(REF, spaces_in["INBOX"])
    feature = feature_of(dim, work)
    step = feature["properties"]["productInformation"]["resourceLineage"][0]["processStep"][0]
    step["source"][0]["sourceCitation"]["title"] = REF + ".htm"
    with pytest.raises(Exception, match="DIMAP header"):
        PKG.package_one(write_manifest(feature, spaces_in["OUTSPACE"]))


# -- manifest from the synthetic products ------------------------------------------

def test_reference_product_manifest(tmp_path, work):
    dim = copy_product(REF, tmp_path)
    feature = feature_of(dim, work)
    props = feature["properties"]
    acq_info = props["acquisitionInformation"][0]
    acq = acq_info["acquisitionParameters"][0]
    info = props["productInformation"]
    step = info["resourceLineage"][0]["processStep"][0]
    assert feature["id"] == props["title"] == REF_EO_NAME
    assert feature["geometry"]["coordinates"] == \
        [[[10.0, 50.0], [11.0, 47.0], [15.0, 47.5], [14.0, 50.5], [10.0, 50.0]]]
    assert props["date"] == "2009-02-10T10:11:12.000Z/2009-02-10T10:11:12.000Z"
    assert acq_info["platform"] == {"platformShortName": "Beijing-1",
                                    "platformSerialIdentifier": "1", "orbitType": "LEO"}
    assert acq["resolution"] == 32.5
    assert acq["acquisitionAngles"] == {"illuminationAzimuthAngle": 140.5,
                                        "illuminationElevationAngle": 35.25}
    assert info["size"] == sum(p.stat().st_size for p in dim.parent.iterdir())
    assert info["productType"] == "L1_OPT_MS_"
    assert info["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert info["processingDate"] == "2009-03-02T00:00:00.000Z"
    assert step["source"][0] == {"sourceCitation": {"title": dim.name},
                                 "processedLevel": {"code": "L1R"}}
    assert props["links"]["measurements"][0]["href"] == "/measurements/%s" % dim.name
    for key in ("cloudCover", "orbitNumber", "orbitDirection",
                "alongTrackIncidenceAngle", "acrossTrackIncidenceAngle"):
        assert '"%s"' % key not in json.dumps(feature)


def test_side_product_manifest_has_cloud_cover(tmp_path, work):
    feature = feature_of(copy_product(SIDE, tmp_path), work)
    # alone in its registry, it gets counter 01
    assert feature["id"] == REF_EO_NAME
    assert feature["properties"]["productInformation"]["cloudCover"] == 12.5


# -- manifest against the reference template ------------------------------------

DMC_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "DMC-template.json"
REF_DIM = "DC00068e_000000_010499_p_L1R_FI.dim"
OPTIONAL_KEYS = ["orbitNumber", "orbitDirection", "cloudCover", "referenceSystemIdentifier",
                 "alongTrackIncidenceAngle", "acrossTrackIncidenceAngle"]
SAR_KEYS = ["polarisationMode", "polarisationChannels", "antennaLookDirection",
            "rangeResolution", "azimuthResolution"]


def _reference():
    with open(DMC_TEMPLATE, encoding="utf-8") as fd:
        return json.load(fd)


def _filled_metadata(ref, prefix="BJ1", level="L1R", optional=True):
    """Metadata filled by hand with the reference template's values (the
    template carries fields the deliveries lack, e.g. the orbit)."""
    met = M.Metadata(None)
    prod = P.Product_DMC.__new__(P.Product_DMC)
    prod.metadata = met
    prod.dim_name = REF_DIM
    prod.tmpSize = ref["properties"]["productInformation"]["size"]
    prod.set_platform(prefix)
    prod.set_level(level)
    acq = ref["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]
    met.setMetadataPair(P.CREATION_TIME, ref["properties"]["created"])
    met.setMetadataPair(M.METADATA_START_DATE_TIME, acq["beginningDateTime"])
    met.setMetadataPair(M.METADATA_STOP_DATE_TIME, acq["endingDateTime"])
    met.setMetadataPair(M.METADATA_RESOLUTION, acq["resolution"])
    met.setMetadataPair(M.METADATA_SUN_AZIMUTH, acq["acquisitionAngles"]["illuminationAzimuthAngle"])
    met.setMetadataPair(M.METADATA_SUN_ELEVATION, acq["acquisitionAngles"]["illuminationElevationAngle"])
    met.setMetadataPair(M.METADATA_PROCESSING_TIME,
                        ref["properties"]["productInformation"]["processingDate"])
    met.addLocalAttribute("footprintRing", ref["geometry"]["coordinates"][0])
    if optional:
        met.setMetadataPair(M.METADATA_ORBIT, acq["orbitNumber"])
        met.setMetadataPair(M.METADATA_ORBIT_DIRECTION, acq["orbitDirection"])
        met.setMetadataPair(M.METADATA_CLOUD_COVERAGE,
                            ref["properties"]["productInformation"]["cloudCover"])
        met.addLocalAttribute("referenceSystemIdentifier",
                              ref["properties"]["productInformation"]["referenceSystemIdentifier"])
    return met, prod


def _manifest_feature(met, prod, eo_name):
    feature = json_template.build(*E.build_layers(met, prod, eo_name),
                                  template_path=E.TEMPLATE_PATH)
    json_template.validate(feature)
    return feature


def test_reference_template_fills_the_placeholder_template():
    ref = _reference()
    merged = json_template.build(ref, template_path=E.TEMPLATE_PATH)
    json_template.validate(merged)
    assert merged == ref


def test_emitted_manifest_equals_the_reference_template():
    ref = _reference()
    met, prod = _filled_metadata(ref)
    assert _manifest_feature(met, prod, ref["id"]) == ref


def test_optional_fields_are_left_out_when_absent():
    ref = _reference()
    met, prod = _filled_metadata(ref, optional=False)
    text = json.dumps(_manifest_feature(met, prod, ref["id"]))
    for key in OPTIONAL_KEYS:
        assert '"%s"' % key not in text


def test_missing_mandatory_value_fails_with_its_path():
    ref = _reference()
    met, prod = _filled_metadata(ref)
    met.setMetadataPair(M.METADATA_RESOLUTION, None)
    with pytest.raises(ValueError, match=r"acquisitionParameters\[0\]\.resolution"):
        _manifest_feature(met, prod, ref["id"])


def test_ending_time_defaults_to_beginning_time():
    # spec Table 11: no ending time -> the beginning time
    ref = _reference()
    met, prod = _filled_metadata(ref)
    met.setMetadataPair(M.METADATA_STOP_DATE_TIME, None)
    feature = _manifest_feature(met, prod, ref["id"])
    acq = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert acq["endingDateTime"] == acq["beginningDateTime"]
    assert feature["properties"]["date"] == "%s/%s" % (acq["beginningDateTime"], acq["beginningDateTime"])


@pytest.mark.parametrize("prefix,platform", [
    ("BJ1", "Beijing-1"), ("NG1", "NigeriaSat-1"), ("UK1", "UK-DMC-1")])
@pytest.mark.parametrize("level,typecode", [("L1R", "L1_OPT_MS_"), ("L1T", "L1_ORT_MS_")])
def test_platform_and_product_type_per_satellite(prefix, platform, level, typecode):
    ref = _reference()
    met, prod = _filled_metadata(ref, prefix=prefix, level=level)
    eo_name = "%s_OPER_%s_20170424T134911_20170424T135006_0001" % (prefix, typecode)
    feature = _manifest_feature(met, prod, eo_name)
    props = feature["properties"]
    acq_info = props["acquisitionInformation"][0]
    step = props["productInformation"]["resourceLineage"][0]["processStep"][0]
    assert len(eo_name) == 56 and feature["id"] == props["title"] == eo_name
    assert acq_info["platform"] == {"platformShortName": platform,
                                    "platformSerialIdentifier": "1", "orbitType": "LEO"}
    assert props["productInformation"]["productType"] == typecode
    assert step["source"][0]["processedLevel"]["code"] == level
    assert step["output"][0]["sourceCitation"]["title"] == eo_name + ".ZIP"
    assert props["links"]["previews"][0]["href"] == "/previews/overviews/%s.PNG" % eo_name


def test_fixed_values_follow_the_specification():
    ref = _reference()
    met, prod = _filled_metadata(ref)
    props = _manifest_feature(met, prod, ref["id"])["properties"]
    acq_info = props["acquisitionInformation"][0]
    acq = acq_info["acquisitionParameters"][0]
    step = props["productInformation"]["resourceLineage"][0]["processStep"][0]
    links = props["links"]
    assert props["status"] == "ACQUIRED"
    assert acq_info["instrument"] == {"instrumentShortName": "SLIM6", "sensorType": "OPTICAL"}
    assert (acq["operationalMode"], acq["acquisitionType"]) == ("MS3B", "NOMINAL")
    assert acq["wavelengths"] == P.wavelengths()
    assert props["productInformation"]["processingLevel"] == "1"
    assert step["description"] == "EOPF-EOS Converter for Beijing-1, Nigeriasat-1 and UK-DMC-1"
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": E.SPEC_TITLE, "edition": "1.0"}]
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["source"][0]["sourceCitation"]["title"] == REF_DIM
    assert links["measurements"] == [{"href": "/measurements/%s" % REF_DIM,
                                      "type": "application/xml",
                                      "title": "Native EO Product", "category": "DATA"}]
    assert links["previews"][0]["type"] == "image/png"
    assert links["previews"][0]["title"] == "Preview MS Image"
    assert links["previews"][0]["category"] == "OVERVIEW"


def test_no_sar_fields_and_lineage_citation_round_trip():
    ref = _reference()
    met, prod = _filled_metadata(ref)
    feature = _manifest_feature(met, prod, ref["id"])
    text = json.dumps(feature)
    for key in SAR_KEYS:
        assert '"%s"' % key not in text
    # the packager and run_mission find the native back through this citation
    assert json_template.lineage_citation(feature) == REF_DIM
