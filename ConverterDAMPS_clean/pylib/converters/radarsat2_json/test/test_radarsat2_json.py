"""Structural proof: drive radarsat2_json extraction on synthetic RADARSAT-2
products, emit the JSON manifest via the common template generator, and
assert the output matches feature_template_rs2.json key-path for key-path,
with the values the specialization asks for.

Fixtures (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): four synthetic product
folders written by fixtures/make_synthetic_rs2.py - no real RADARSAT-2
product was available.
"""
import json
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from radarsat2_json import product_radarsat2, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_rs2"
NS = "http://www.rsi.ca/rs2/prod/xml/schemas"


def _product(beam):
    return next(FIXTURE_DIR.glob("RS2_*_%s_*/product.xml" % beam))


FW_SLC = _product("F0W2")
S3_SGF = _product("S3")
FQ_SSG = _product("FQ14")
SCW = _product("SCWA")
ALL = [FW_SLC, S3_SGF, FQ_SSG, SCW]

# the 41 product types of the specialization, section 1.1 and Table 2
ALLOWED_PRODUCT_TYPES = {
    "L1_BS__SGF", "L1_BS__SGX", "L1_BS__SLC", "L2_BS__SSG", "L2_BS__SPG",
    "L1_BSF_SGF", "L1_BSF_SGX", "L1_BSF_SLC", "L2_BSF_SSG", "L2_BSF_SPG",
    "L1_BSW_SGF", "L1_BSW_SGX", "L1_BSW_SLC", "L2_BSW_SSG", "L2_BSW_SPG",
    "L1_BSWFSGF", "L1_BSWFSGX", "L1_BSWFSLC", "L2_BSWFSSG", "L2_BSWFSPG",
    "L1_ML__SGF", "L1_ML__SGX", "L1_ML__SLC", "L2_ML__SSG", "L2_ML__SPG",
    "L1_MLW_SGF", "L1_MLW_SGX", "L1_MLW_SLC", "L2_MLW_SSG", "L2_MLW_SPG",
    "L1_SL__SGF", "L1_SL__SGX", "L1_SL__SLC", "L2_SL__SSG", "L2_SL__SPG",
    "L1_SCN____", "L1_SCN_SCF", "L1_SCN_SCS",
    "L1_SCW____", "L1_SCW_SCF", "L1_SCW_SCS",
}

OPTICAL_KEYS = ["cloudCover", "illuminationAzimuthAngle", "illuminationElevationAngle"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(xml_path, work_folder):
    prod = product_radarsat2.Product_Radarsat2(str(xml_path))
    prod.setDebug(0)
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, _ProcessInfoStub(str(work_folder)))
    return prod, met


def _feature(xml_path, work_folder, eo_name="RS2_OPER_TEST"):
    prod, met = _extract(xml_path, work_folder)
    # the ingester passes the product folder name, as here
    mission, dynamic = json_emitter.build_layers(
        met, prod, eo_name, native_product_name=prod.productName)
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


def _acq(feature):
    return feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]


def _copy(xml_path, tmp_path):
    """Writable copy of a fixture product folder; returns its product.xml."""
    dest = tmp_path / xml_path.parent.name
    shutil.copytree(xml_path.parent, dest)
    return dest / "product.xml"


def _edit(xml_path, tmp_path, edit):
    """Copy a fixture, apply edit(root) to its product.xml (namespace kept)."""
    target = _copy(xml_path, tmp_path)
    ET.register_namespace("", NS)
    tree = ET.parse(target)
    edit(tree.getroot(), "{%s}" % NS)
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


@pytest.mark.parametrize("xml_path", ALL, ids=lambda p: p.parent.name.split("_")[4])
def test_emitted_json_matches_template_structure(xml_path, tmp_path):
    _, _, feature = _feature(xml_path, tmp_path)
    json_template.validate(feature)

    with open(json_emitter.TEMPLATE_PATH, encoding="utf-8") as fd:
        template = json.load(fd)
    template["geometry"]["coordinates"] = feature["geometry"]["coordinates"]
    got, want = _key_paths(feature), _key_paths(template)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))

    text = json.dumps(feature)
    for key in OPTICAL_KEYS:
        assert key not in text
    assert feature["properties"]["productInformation"]["productType"] in ALLOWED_PRODUCT_TYPES

    ring = feature["geometry"]["coordinates"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert ring[0] == ring[-1] and len(ring) == 5


def test_wide_fine_slc_values(tmp_path):
    prod, met, feature = _feature(FW_SLC, tmp_path)
    props = feature["properties"]
    acq = _acq(feature)
    pinfo = props["productInformation"]
    step = pinfo["resourceLineage"][0]["processStep"][0]

    assert pinfo["productType"] == "L1_BSWFSLC"
    assert acq["operationalMode"] == "BSWF"
    assert acq["beginningDateTime"] == "2010-05-27T23:16:08.123Z"
    assert acq["endingDateTime"] == "2010-05-27T23:16:12.987Z"
    assert props["date"] == "2010-05-27T23:16:08.123Z/2010-05-27T23:16:12.987Z"
    assert acq["polarisationMode"] == "D"
    assert acq["polarisationChannels"] == "HH, HV"
    assert acq["antennaLookDirection"] == "RIGHT"
    assert acq["rangeResolution"] == pytest.approx(8.208, abs=1e-3)
    assert acq["azimuthResolution"] == pytest.approx(7.369, abs=1e-3)
    assert acq["resolution"] == acq["rangeResolution"]
    assert acq["acquisitionAngles"]["incidenceAngle"] == 37.5
    assert acq["orbitNumber"] == 13034
    assert acq["orbitDirection"] == "ASCENDING"
    assert acq["acquisitionType"] == "NOMINAL"
    assert acq["wavelengths"] == [{"spectralRange": "C", "discreteWavelengths": [0.0554658]}]

    acquisition = props["acquisitionInformation"][0]
    assert acquisition["platform"] == {"platformShortName": "RADARSAT-2", "orbitType": "LEO"}
    assert acquisition["instrument"] == {"instrumentShortName": "SAR", "sensorType": "RADAR"}

    assert props["status"] == "ACQUIRED"
    assert props["title"] == feature["id"] == "RS2_OPER_TEST"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert pinfo["processingLevel"] == "1"
    assert pinfo["processingDate"] == "2010-05-28T02:11:45.000Z"
    assert pinfo["size"] == prod.tmpSize
    assert step["description"] == "EOPF-EOS Converter for RADARSAT-2"
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for RADARSAT-2 products",
                                  "edition": "1.0"}]
    assert step["source"][0]["sourceCitation"]["title"] == FW_SLC.parent.name
    assert step["source"][0]["processedLevel"]["code"] == "L1"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["output"][0]["sourceCitation"]["title"] == "RS2_OPER_TEST.ZIP"
    assert step["processingInformation"]["softwareReference"]["title"] == "EOPF-EOS Converter for RADARSAT-2"

    links = props["links"]
    assert links["measurements"][0] == {
        "href": "/measurements/%s/imagery_HH.tif" % FW_SLC.parent.name,
        "type": "image/tiff", "title": "Native EO Product", "category": "DATA"}
    assert links["previews"][0] == {"href": "/previews/overviews/RS2_OPER_TEST.PNG",
                                    "type": "image/png", "title": "Preview Image",
                                    "category": "OVERVIEW"}

    ring = feature["geometry"]["coordinates"][0]
    assert {(lon, lat) for lon, lat in ring} == {
        (-73.701, 45.512), (-73.012, 45.598), (-72.901, 45.112), (-73.587, 45.031)}


def test_standard_sgf_orbit_from_prod_report(tmp_path):
    _, _, feature = _feature(S3_SGF, tmp_path)
    acq = _acq(feature)
    assert feature["properties"]["productInformation"]["productType"] == "L1_BS__SGF"
    assert acq["operationalMode"] == "BS"
    assert acq["polarisationMode"] == "S"
    assert acq["polarisationChannels"] == "HH"
    # the orbit data file name carries no number: the .prodReport gives it
    assert acq["orbitNumber"] == 23861
    assert acq["orbitDirection"] == "DESCENDING"


def test_quad_pol_map_image_utm(tmp_path):
    _, _, feature = _feature(FQ_SSG, tmp_path)
    acq = _acq(feature)
    pinfo = feature["properties"]["productInformation"]
    step = pinfo["resourceLineage"][0]["processStep"][0]
    assert pinfo["productType"] == "L2_BSF_SSG"
    assert acq["polarisationMode"] == "Q"
    assert acq["polarisationChannels"] == "HH, HV, VH, VV"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32633"
    assert pinfo["processingLevel"] == "2"
    assert step["source"][0]["processedLevel"]["code"] == "L2"


def test_scansar_wide_left_looking(tmp_path):
    _, _, feature = _feature(SCW, tmp_path)
    acq = _acq(feature)
    assert feature["properties"]["productInformation"]["productType"] == "L1_SCW____"
    assert acq["operationalMode"] == "SCW"
    assert acq["antennaLookDirection"] == "LEFT"
    # schema value order, whatever the native order (VV VH)
    assert acq["polarisationChannels"] == "VH, VV"


@pytest.mark.parametrize("beam, mode", [
    ("S1", "BS"), ("EH3", "BS"), ("EL1", "BS"), ("SQ12", "BS"),
    ("W2", "BSW"), ("SQ5W", "BSW"),
    ("F1", "BSF"), ("F23N", "BSF"), ("U12", "BSF"), ("FQ20", "BSF"),
    ("F0W3", "BSWF"), ("U3W2", "BSWF"), ("XF0W1", "BSWF"), ("FQ9W", "BSWF"),
    ("MF3", "ML"), ("MF22F", "ML"), ("MF6W", "MLW"),
    ("SLA22", "SL"), ("SCNA", "SCN"), ("SCWB", "SCW"),
])
def test_beam_mode_to_operational_mode(beam, mode):
    assert product_radarsat2.operational_mode(beam) == mode


def test_unknown_beam_mode_fails():
    with pytest.raises(Exception, match="unsupported RADARSAT-2 beam mode"):
        product_radarsat2.operational_mode("OSVN")


def test_type_code_table_matches_spec():
    assert set(product_radarsat2.TYPECODE_MAP.values()) == ALLOWED_PRODUCT_TYPES
    assert all(len(code) == 10 for code in ALLOWED_PRODUCT_TYPES)


def test_scansar_product_type_must_match_mode(tmp_path):
    def edit(root, ns):
        root.find("%simageGenerationParameters/%sgeneralProcessingInformation/%sproductType"
                  % (ns, ns, ns)).text = "SCN"
    target = _edit(SCW, tmp_path, edit)
    with pytest.raises(Exception, match="unsupported RADARSAT-2 product: SCN"):
        _extract(target, tmp_path)


def test_quad_pol_not_allowed_for_scansar(tmp_path):
    def edit(root, ns):
        root.find("%ssourceAttributes/%sradarParameters/%spolarizations"
                  % (ns, ns, ns)).text = "HH VV HV VH"
    target = _edit(SCW, tmp_path, edit)
    with pytest.raises(Exception, match="polarisation mode Q not allowed"):
        _extract(target, tmp_path)


def test_orbit_fallback_keeps_cfg_value(tmp_path):
    target = _copy(S3_SGF, tmp_path)
    for report in target.parent.glob("*.prodReport"):
        report.unlink()
    prod = product_radarsat2.Product_Radarsat2(str(target))
    prod.extractToPath(str(tmp_path))
    met = M.Metadata(None)
    met.setMetadataPair(M.METADATA_ORBIT, "0")  # the cfg METADATA_ORBIT
    prod.extractMetadata(met, _ProcessInfoStub(str(tmp_path)))
    assert met.getMetadataValue(M.METADATA_ORBIT) == "0"


def test_not_radarsat2_fails(tmp_path):
    def edit(root, ns):
        root.find("%ssourceAttributes/%ssatellite" % (ns, ns)).text = "RADARSAT-1"
    target = _edit(FW_SLC, tmp_path, edit)
    with pytest.raises(Exception, match="not a RADARSAT-2 product"):
        _extract(target, tmp_path)


@pytest.mark.parametrize("xml_path", ALL, ids=lambda p: p.parent.name.split("_")[4])
def test_quicklook_png(xml_path, tmp_path):
    prod, _ = _extract(xml_path, tmp_path)
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    with Image.open(png) as image, Image.open(prod.browse_file()) as browse:
        assert image.format == "PNG"
        assert image.size == browse.size


def test_packager_finds_native_by_folder_citation(tmp_path, monkeypatch):
    """The citation is the product folder name: the packager stores that
    folder under measurements/ and the overview under previews/overviews/."""
    from radarsat2_json import package_radarsat2_zips as pkg
    from common import spaces

    inbox, out, products = tmp_path / "INBOX", tmp_path / "OUTSPACE", tmp_path / "PRODUCTS"
    for d in (inbox, out, products):
        d.mkdir()
    target = _copy(FW_SLC, inbox)
    work = tmp_path / "work"
    work.mkdir()
    prod, _, feature = _feature(target, work)
    (out / "RS2_OPER_TEST.JSON").write_text(json.dumps(feature), encoding="utf-8")
    prod.writeQuicklook(str(out / "RS2_OPER_TEST.PNG"))

    roots = {"INBOX": inbox, "OUTSPACE": out, "PRODUCTS": products,
             "TMPSPACE": tmp_path / "TMP", "DONESPACE": tmp_path / "DONE",
             "FAILEDSPACE": tmp_path / "FAILED"}
    monkeypatch.setattr(pkg, "SPACES", dict(pkg.SPACES, **roots))
    monkeypatch.setattr(pkg, "OUTSPACE", out)
    monkeypatch.setattr(pkg, "PRODUCTS", products)
    assert spaces.find_native(FW_SLC.parent.name, pkg.SPACES) == target.parent

    native = pkg.package_one(out / "RS2_OPER_TEST.JSON")
    assert native == target.parent
    with zipfile.ZipFile(products / "RS2_OPER_TEST.ZIP") as zf:
        names = set(zf.namelist())
        assert all(info.compress_type == zipfile.ZIP_STORED for info in zf.infolist())
    assert "RS2_OPER_TEST.JSON" in names
    assert "previews/overviews/RS2_OPER_TEST.PNG" in names
    assert "measurements/%s/product.xml" % FW_SLC.parent.name in names
    assert "measurements/%s/imagery_HH.tif" % FW_SLC.parent.name in names
