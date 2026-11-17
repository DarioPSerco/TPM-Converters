"""Structural proof: drive kompsat_json extraction on SYNTHETIC native KOMPSAT
products, emit the JSON manifest via the common template generator, and assert
the output matches TDS/template/KO-template.json key-path for key-path, plus
the values the specialization fixes.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): no real
KOMPSAT product has been run yet. The footprint and angles are the ones of the
specialization's example manifests.
"""
import configparser
import importlib
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from kompsat_json import json_emitter, kompsat_files, product_kompsat

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_ko"
FLAT_DIR = FIXTURE_DIR / "k2_flat"
FLAT_XML = FLAT_DIR / "MSC_100607044108_21000_10731074PN11_1G.txt"
SPLIT_SCENE = FIXTURE_DIR / "k2_split" / "MSC_090415014422_15130_11831188_1R"
SPLIT_TXT = SPLIT_SCENE / "PAN" / "MSC_090415014422_15130_11831188PN00_1R.txt"
K1_DIR = FIXTURE_DIR / "k1_ortho"
K1_TXT = K1_DIR / "EOC_020101121314_00042_L1B.txt"
KO_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "KO-template.json"

FLAT_EO_NAME = "KO2_OPER_L1_GEO_BDL_20100607T044108_20100607T044112_0000"
SPLIT_EO_NAME = "KO2_OPER_L1_OPT_BDL_20090415T014422_20090415T014422_0000"
K1_EO_NAME = "KO1_OPER_L1BORT_PAN_20020101T121314_20020101T121417_0000"

EXAMPLE_RING = [[-66.44291264, -24.15261009], [-66.44136086, -24.23036597],
                [-66.36391186, -24.22904374], [-66.36551048, -24.15129263],
                [-66.44291264, -24.15261009]]

SAR_KEYS = ["polarisationMode", "polarisationChannel", "rangeResolution",
            "azimuthResolution", "antennaLookDirection", "platformSerialIdentifier"]
OTHER_MISSION_TOKENS = ["GeoEye", "WorldView", "QuickBird", "Pleiades", "ICEYE",
                        "COSMO", "RADAR", "PlanetScope", "SkySat", "Rapideye", "GEOSAT"]


def _extract(entry, work_folder):
    prod = product_kompsat.Product_Kompsat(str(entry))
    prod.setDebug(0)
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, None)
    return prod, met


def _feature(entry, eo_name, work_folder):
    prod, met = _extract(entry, work_folder)
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


def _copy_product(tmp_path, source_dir):
    folder = tmp_path / "product"
    shutil.copytree(source_dir, folder)
    return folder


def _edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def test_emitted_json_matches_ko_template_structure(work):
    _, _, feature = _feature(FLAT_XML, FLAT_EO_NAME, work)
    json_template.validate(feature)
    with open(KO_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_geo_bundle_values(work):
    prod, _, feature = _feature(FLAT_XML, FLAT_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    pan, ms = acq["acquisitionParameters"]

    assert feature["id"] == props["title"] == FLAT_EO_NAME
    assert feature["geometry"] == {"type": "Polygon", "coordinates": [EXAMPLE_RING]}
    assert props["status"] == "ACQUIRED"
    assert props["date"] == "2010-06-07T04:41:08.800Z/2010-06-07T04:41:12.300Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "KOMPSAT-2", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "MSC", "sensorType": "OPTICAL"}

    assert pan["operationalMode"] == "PAN" and ms["operationalMode"] == "MS4B"
    assert pan["resolution"] == 1.0 and ms["resolution"] == 4.0
    assert pan["beginningDateTime"] == "2010-06-07T04:41:08.800Z"
    assert ms["beginningDateTime"] == "2010-06-07T04:41:08.900Z"  # the MS component's own AUX
    for par in (pan, ms):
        assert par["acquisitionType"] == "NOMINAL"
        assert par["orbitNumber"] == 21000 and isinstance(par["orbitNumber"], int)
        assert par["orbitDirection"] == "DESCENDING"
        assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                            "illuminationElevationAngle": 44.1,
                                            "alongTrackIncidenceAngle": 0.7,
                                            "acrossTrackIncidenceAngle": 0.8}
    assert pan["wavelengths"] == [{"spectralRange": "VNIR", "startWavelength": 500e-9,
                                   "endWavelength": 900e-9, "discreteWavelengths": [700e-9]}]
    assert ms["wavelengths"] == [
        {"spectralRange": "VIS", "startWavelength": 450e-9, "endWavelength": 690e-9,
         "discreteWavelengths": [485e-9, 560e-9, 660e-9]},
        {"spectralRange": "NIR", "startWavelength": 760e-9, "endWavelength": 900e-9,
         "discreteWavelengths": [830e-9]},
    ]

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1_GEO_BDL"
    assert pinfo["processingLevel"] == "1"
    assert pinfo["processingDate"] == "2010-06-08T10:20:30.000Z"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert pinfo["cloudCover"] == 10.0
    assert pinfo["size"] == sum(p.stat().st_size for p in FLAT_DIR.iterdir())
    assert len(prod.files) == 5  # PAN + MS image and metadata, RPC text

    step = pinfo["resourceLineage"][0]["processStep"]
    assert len(step) == 1
    step = step[0]
    assert step["description"] == "EOPF-EOS Converter for KOMPSAT"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for KOMPSAT products",
                                  "edition": "1.0"}]
    assert step["source"] == [{"sourceCitation": {"title": FLAT_XML.name},
                               "processedLevel": {"code": "L1G"}}]
    assert step["processingInformation"]["softwareReference"] == {
        "title": "EOPF-EOS Converter for KOMPSAT", "edition": "1.0.0"}
    assert step["output"] == [{"sourceCitation": {"title": "%s.ZIP" % FLAT_EO_NAME}}]

    assert props["links"] == {
        "measurements": [{"href": "/measurements/MSC_100607044108_21000_10731074PN11_1G.tif",
                          "type": "image/tiff", "title": "Native EO Product", "category": "DATA"}],
        "previews": [{"href": "/previews/overviews/%s.PNG" % FLAT_EO_NAME,
                      "type": "image/png", "title": "Preview Image", "category": "OVERVIEW"}],
    }


def test_split_bundle_values(work):
    prod, _, feature = _feature(SPLIT_TXT, SPLIT_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    pan, ms = props["acquisitionInformation"][0]["acquisitionParameters"]
    pinfo = props["productInformation"]

    # the product root is the scene folder holding PAN/ and MS/
    assert prod.EO_FOLDER == str(SPLIT_SCENE)
    assert len(prod.files) == 8
    assert pinfo["productType"] == "L1_OPT_BDL"
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1R"
    # no end time: set to the beginning (Table 11); no processing date: the beginning (Table 18)
    assert pan["beginningDateTime"] == pan["endingDateTime"] == "2009-04-15T01:44:22.500Z"
    assert pinfo["processingDate"] == "2009-04-15T01:44:22.500Z"
    assert ms["endingDateTime"] == "2009-04-15T01:44:25.100Z"
    assert pan["orbitDirection"] == "ASCENDING"
    assert "acquisitionAngles" not in pan and "acquisitionAngles" not in ms  # optional for KOMPSAT-2
    assert "cloudCover" not in pinfo  # native -1: not assessed
    assert feature["geometry"]["coordinates"] == [EXAMPLE_RING]  # UL/UR/LR/LL corner keys
    assert props["links"]["measurements"][0]["href"] == \
        "/measurements/PAN/MSC_090415014422_15130_11831188PN00_1R.tif"


def test_kompsat1_values(work):
    _, _, feature = _feature(K1_TXT, K1_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    pinfo = props["productInformation"]
    assert acq["platform"]["platformShortName"] == "KOMPSAT-1"
    assert acq["instrument"]["instrumentShortName"] == "EOC"
    (par,) = acq["acquisitionParameters"]
    assert par["operationalMode"] == "PAN"
    assert par["resolution"] == 6.6
    assert par["wavelengths"] == [{"spectralRange": "VNIR", "startWavelength": 510e-9,
                                   "endWavelength": 730e-9, "discreteWavelengths": [620e-9]}]
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1}
    assert pinfo["productType"] == "L1BORT_PAN"
    assert pinfo["processingLevel"] == "1B"
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1B"
    assert pinfo["cloudCover"] == 0.0
    ring = feature["geometry"]["coordinates"][0]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    assert area > 0, "footprint must be counter-clockwise (RFC 7946)"


def test_kompsat1_needs_an_acquisition_angle(tmp_path, work):
    folder = _copy_product(tmp_path, K1_DIR)
    entry = folder / K1_TXT.name
    _edit(entry, "AUX_SUN_AZIMUTH_ANGLE_DEG   33.3\n", "")
    _edit(entry, "AUX_SUN_ELEVATION_ANGLE_DEG 44.1\n", "")
    with pytest.raises(Exception, match="mandatory for KOMPSAT-1"):
        _extract(entry, work)


def test_lineage_citation_is_the_entry_file(work):
    _, _, feature = _feature(SPLIT_TXT, SPLIT_EO_NAME, work)
    assert json_template.lineage_citation(feature) == SPLIT_TXT.name


@pytest.mark.parametrize("entry,source", [
    (FLAT_XML, "MS11_1G.tif"), (SPLIT_TXT, "_br.jpg"), (K1_TXT, "L1B.tif")])
def test_overview_png(tmp_path, entry, source, capsys):
    prod = product_kompsat.Product_Kompsat(str(entry))
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    assert source in capsys.readouterr().out

    from PIL import Image
    with Image.open(png) as im:
        assert im.format == "PNG" and im.mode == "RGBA"
        assert im.size == (16, 12)
        if entry != SPLIT_TXT:  # rendered: the zero first column is transparent
            assert im.getpixel((0, 5))[3] == 0
            assert im.getpixel((8, 5))[3] == 255


def test_overview_from_ms_band_images(tmp_path):
    folder = _copy_product(tmp_path, SPLIT_SCENE)
    (folder / "PAN" / "MSC_090415014422_15130_11831188PN00_1R_br.jpg").unlink()
    prod = product_kompsat.Product_Kompsat(str(folder / "PAN" / SPLIT_TXT.name))
    assert prod.browse_file is None
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    from PIL import Image
    with Image.open(png) as im:
        assert im.size == (16, 12) and im.getpixel((0, 5))[3] == 0


def test_bundle_without_ms_is_rejected(tmp_path):
    folder = _copy_product(tmp_path, FLAT_DIR)
    for p in folder.glob("*MS11*"):
        p.unlink()
    with pytest.raises(Exception, match="without MS component"):
        product_kompsat.Product_Kompsat(str(folder / FLAT_XML.name))


def test_ms_entry_is_rejected():
    with pytest.raises(Exception, match="must be the PAN metadata"):
        product_kompsat.Product_Kompsat(str(FLAT_DIR / "MSC_100607044108_21000_10731074MS11_1G.txt"))


@pytest.mark.parametrize("old,new,message", [
    ("AUX_ORBIT_DIRECTION         DESCENDING", "AUX_ORBIT_DIRECTION         SIDEWAYS",
     "invalid or missing orbit direction"),
    ("AUX_IMAGE_TL_LATITUDE_DEC    -24.15261009", "AUX_IMAGE_TL_LATITUDE_DEC    -124.15261009",
     "out of range"),
    ("AUX_PROCESSING_LEVEL        1G", "AUX_PROCESSING_LEVEL        1R", "differ"),
    ("AUX_SATELLITE_NAME          KOMPSAT-2", "AUX_SATELLITE_NAME          KOMPSAT-3",
     "KOMPSAT-1 and -2 only"),
])
def test_invalid_metadata_is_rejected(tmp_path, work, old, new, message):
    folder = _copy_product(tmp_path, FLAT_DIR)
    entry = folder / FLAT_XML.name
    _edit(entry, old, new)
    with pytest.raises(Exception, match=message):
        _extract(entry, work)


def test_missing_corners_are_rejected(tmp_path, work):
    folder = _copy_product(tmp_path, K1_DIR)
    entry = folder / K1_TXT.name
    text = "".join(line for line in entry.read_text(encoding="utf-8").splitlines(True)
                   if "_TL_" not in line)
    entry.write_text(text, encoding="utf-8")
    with pytest.raises(Exception, match="no footprint corners"):
        _extract(entry, work)


def test_entry_must_be_aux_metadata(tmp_path):
    bogus = tmp_path / "EOC_x.txt"
    bogus.write_text("hello world\n", encoding="utf-8")
    with pytest.raises(Exception, match="no AUX_ keys"):
        product_kompsat.Product_Kompsat(str(bogus))
    with pytest.raises(Exception, match="not a KOMPSAT AUX metadata file"):
        product_kompsat.Product_Kompsat(str(tmp_path / "EOC_x.xml"))


def test_aux_parser_groups_and_separators(tmp_path):
    aux = tmp_path / "a.txt"
    aux.write_text("# comment\nBEGIN_PAN\n  AUX_A  1\nEND_PAN\nAUX_B = \"two words\"\nAUX_EMPTY\n",
                   encoding="utf-8")
    assert kompsat_files.parse_aux(aux) == {"PAN.AUX_A": "1", "AUX_A": "1", "AUX_B": "two words"}


@pytest.mark.parametrize("date,time,expected", [
    ("20100607", "04:41:08.800000", "2010-06-07T04:41:08.800Z"),
    ("2009-04-15", "014422.5", "2009-04-15T01:44:22.500Z"),
    ("2002/01/01", "12:13:14", "2002-01-01T12:13:14.000Z"),
    ("2010-06-07T04:41:08.123456Z", None, "2010-06-07T04:41:08.123Z"),
])
def test_datetime_parsing(date, time, expected):
    assert product_kompsat.parse_utc(date, time) == expected


def test_name_time():
    assert product_kompsat.name_time("100607044108") == "2010-06-07T04:41:08.000Z"
    assert product_kompsat.name_time("991231235959") == "1999-12-31T23:59:59.000Z"


def test_msc_names():
    fields = kompsat_files.msc_name("MSC_100607044108_21000_10731074PN11_1G.tif")
    assert (fields["time"], fields["orbit"], fields["mode"], fields["level"]) == \
        ("100607044108", "21000", "PN", "1G")
    assert kompsat_files.scene_key("MSC_100607044108_21000_10731074M311_1G.tif") == \
        kompsat_files.scene_key("MSC_100607044108_21000_10731074PN11_1G_br.jpg")
    assert kompsat_files.msc_name("EOC_020101121314_00042_L1B.txt") is None


def test_entry_pattern_selects_pan_metadata_only():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(Path(product_kompsat.__file__).resolve().parent / "ingest_kompsat.cfg")
    name = re.compile(cfg.get("Search", "FILES_NAMEPATTERN"))
    ext = re.compile(cfg.get("Search", "FILES_EXTPATTERN"))
    assert name.match("MSC_100607044108_21000_10731074PN11_1G")
    assert name.match("msc_100607044108_21000_10731074pn11_1r")
    assert name.match("EOC_020101121314_00042_L1B")
    assert not name.match("MSC_100607044108_21000_10731074MS11_1G")
    assert not name.match("MSC_100607044108_21000_10731074M111_1G")
    assert not name.match("MSC_100607044108_21000_10731074PN11_1G_rpc")
    assert ext.match(".txt") and ext.match(".TXT") and not ext.match(".tif")


def test_packager_selects_the_same_product_files():
    packager = importlib.import_module("kompsat_json.package_kompsat_zips")
    for entry in (FLAT_XML, SPLIT_TXT, K1_TXT):
        prod = product_kompsat.Product_Kompsat(str(entry))
        root = packager.F.product_root(entry)
        assert root == prod.EO_FOLDER
        assert packager.F.product_files(entry, root) == prod.files


def test_product_type_table_is_the_specialization_one():
    types = {row[0] for row in product_kompsat.PRODUCT_TYPES.values()}
    assert types == {"L1BORT_PAN", "L1_OPT_BDL", "L1_GEO_BDL"}
    assert all(len(t) == 10 for t in types)
    for (satellite, mode), ranges in product_kompsat.WAVELENGTHS.items():
        assert (satellite, mode) in product_kompsat.RESOLUTIONS
        assert sum(len(b) for _, b in ranges) == (4 if mode == "MS4B" else 1)


def test_sar_fields_and_other_missions_absent(work):
    _, _, feature = _feature(FLAT_XML, FLAT_EO_NAME, work)
    paths = _key_paths(feature)
    for key in SAR_KEYS:
        assert not any(key in p for p in paths), "field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OTHER_MISSION_TOKENS:
        assert tok not in blob, "other-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path, work):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(FLAT_XML, work)
    json_emitter.emit(met, prod, FLAT_EO_NAME, str(out), native_product_name=FLAT_XML.name)
    assert [p.name for p in out.iterdir()] == ["%s.JSON" % FLAT_EO_NAME]
