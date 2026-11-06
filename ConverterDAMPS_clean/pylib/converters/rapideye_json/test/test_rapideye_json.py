"""Structural proof: drive rapideye_json extraction on SYNTHETIC native RapidEye
products, emit the JSON manifest via the common template generator, and assert
the output matches TDS/template/RE-template.json key-path for key-path -
optical fields present, SAR fields absent, no placeholder left.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): no real
RapidEye product has been run yet. The 5-band product carries the values of the
specialization's own example manifest.
"""
import json
import os
import shutil
from pathlib import Path

import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from rapideye_json import product_rapideye, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_re"
DELIVERY_DIR = FIXTURE_DIR / "delivery_re"
L3_STEM = "2017-04-24T134911_RE1_3A-NAC_12345678_123456"
L3_XML = DELIVERY_DIR / ("%s_metadata.xml" % L3_STEM)
L3V_STEM = "1234567_2016-08-12_RE3_3A_654321"
L3V_XML = DELIVERY_DIR / ("%s_metadata.xml" % L3V_STEM)
L1B_STEM = "2012-03-05T101530_RE5_1B-NAC_22334455_778899"
L1B_DIR = FIXTURE_DIR / "basic_re"
L1B_XML = L1B_DIR / ("%s_metadata.xml" % L1B_STEM)
RE_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "RE-template.json"

# EO product names as the naming convention builds them
# (<MMM>_<CCCC>_<TTTTTTTTTT>_<start>_<stop>_<bbvv>)
L3_EO_NAME = "RE__OPER_L3_ORT_MS__20170424T134911_20170424T135111_0001"
L3V_EO_NAME = "RE__OPER_L3_ORT_MS__20160812T100500_20160812T100500_0001"
L1B_EO_NAME = "RE__OPER_L1BOPT_MS__20120305T101530_20120305T101542_0001"

SAR_KEYS = ["polarisationMode", "polarisationChannel", "rangeResolution",
            "azimuthResolution", "antennaLookDirection", "orbitNumber"]
OTHER_MISSION_TOKENS = ["GeoEye", "WorldView", "QuickBird", "Pleiades", "ICEYE",
                        "COSMO", "RADAR", "X-Band", "PlanetScope", "SkySat"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(entry, work_folder):
    prod = product_rapideye.Product_Rapideye(str(entry))
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


def _mutated(tmp_path, source, old, new):
    """Copy of a fixture XML with one edit, next to a copy of its image."""
    folder = tmp_path / "product"
    folder.mkdir(exist_ok=True)
    stem = source.name[:-len("_metadata.xml")]
    for p in source.parent.glob(stem + "*"):
        shutil.copy(p, folder / p.name)
    target = folder / source.name
    text = target.read_text(encoding="utf-8")
    assert old in text, old
    target.write_text(text.replace(old, new), encoding="utf-8")
    return target


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def test_emitted_json_matches_re_template_structure(work):
    _, _, feature = _feature(L3_XML, L3_EO_NAME, work)
    json_template.validate(feature)
    with open(RE_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_five_band_ortho_values(work):
    prod, _, feature = _feature(L3_XML, L3_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    par = acq["acquisitionParameters"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == L3_EO_NAME
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert len(ring) == 5 and ring[0] == ring[-1]
    assert ring[0] == [-66.44291264, -24.15261009]
    assert props["status"] == "ACQUIRED"
    assert props["title"] == L3_EO_NAME
    assert props["date"] == "2017-04-24T13:49:11.000Z/2017-04-24T13:51:11.000Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "RapidEye-1", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "REIS", "sensorType": "OPTICAL"}
    assert par["beginningDateTime"] == "2017-04-24T13:49:11.000Z"
    assert par["endingDateTime"] == "2017-04-24T13:51:11.000Z"
    assert par["acquisitionType"] == "NOMINAL"
    assert par["operationalMode"] == "MS"
    assert par["resolution"] == 5.0
    assert par["orbitDirection"] == "DESCENDING"
    assert par["wavelengths"] == [
        {"spectralRange": "VIS", "startWavelength": 440e-9, "endWavelength": 685e-9,
         "discreteWavelengths": [475e-9, 555e-9, 657.5e-9]},
        {"spectralRange": "VNIR", "startWavelength": 690e-9, "endWavelength": 730e-9,
         "discreteWavelengths": [710e-9]},
        {"spectralRange": "NIR", "startWavelength": 760e-9, "endWavelength": 850e-9,
         "discreteWavelengths": [805e-9]},
    ]
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "acrossTrackIncidenceAngle": -0.7}

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L3_ORT_MS_"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["processingDate"] == "2017-04-25T02:10:33.000Z"
    assert pinfo["cloudCover"] == 0.0
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"
    # only this product's files, not the other product sharing the folder
    assert pinfo["size"] == sum(p.stat().st_size for p in DELIVERY_DIR.glob(L3_STEM + "*"))
    assert len(prod.files) == 4

    steps = pinfo["resourceLineage"][0]["processStep"]
    assert len(steps) == 1
    step = steps[0]
    assert step["description"] == "EOPF-EOS Converter for Rapideye"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for Rapideye products",
                                  "edition": "1.01"}]
    assert step["source"] == [{"sourceCitation": {"title": L3_XML.name},
                               "processedLevel": {"code": "L3"}}]
    assert step["processingInformation"]["softwareReference"] == {
        "title": "EOPF-EOS Converter for Rapideye", "edition": "1.0.0"}
    assert step["output"][0]["sourceCitation"]["title"] == "%s.ZIP" % L3_EO_NAME

    links = props["links"]
    assert links["measurements"] == [{"href": "/measurements/%s.tif" % L3_STEM,
                                      "type": "image/tiff", "title": "Native EO Product",
                                      "category": "DATA"}]
    assert links["previews"] == [{"href": "/previews/overviews/%s.PNG" % L3_EO_NAME,
                                  "type": "image/png", "title": "Preview Image",
                                  "category": "OVERVIEW"}]


def test_three_band_ortho_optional_fields_left_out(work):
    _, _, feature = _feature(L3V_XML, L3V_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert props["acquisitionInformation"][0]["platform"]["platformShortName"] == "RapidEye-3"
    assert [w["spectralRange"] for w in par["wavelengths"]] == ["VIS"]
    assert par["orbitDirection"] == "ASCENDING"
    # empty end time: set to the beginning (Table 11)
    assert par["beginningDateTime"] == par["endingDateTime"] == "2016-08-12T10:05:00.500Z"
    assert "acrossTrackIncidenceAngle" not in par["acquisitionAngles"]
    assert "cloudCover" not in props["productInformation"]  # native -1: not assessed
    assert props["productInformation"]["productType"] == "L3_ORT_MS_"


def test_l1b_values(work):
    prod, _, feature = _feature(L1B_XML, L1B_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    pinfo = props["productInformation"]
    assert props["acquisitionInformation"][0]["platform"]["platformShortName"] == "RapidEye-5"
    assert pinfo["productType"] == "L1BOPT_MS_"
    assert pinfo["processingLevel"] == "1B"
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1B"
    assert pinfo["cloudCover"] == pytest.approx(12.345, abs=0.01)
    assert "referenceSystemIdentifier" not in pinfo
    assert par["resolution"] == 6.5
    assert len(par["wavelengths"]) == 3
    assert len(prod.band_files) == 5
    assert props["links"]["measurements"][0] == {
        "href": "/measurements/%s_band1.ntf" % L1B_STEM,
        "type": "application/octet-stream", "title": "Native EO Product", "category": "DATA"}
    json_template.validate(feature)

    ring = feature["geometry"]["coordinates"][0]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    assert area > 0, "footprint must be counter-clockwise (RFC 7946)"


def test_lineage_citation_is_the_entry_file(work):
    """The runner and the packager find the native product back from it."""
    _, _, feature = _feature(L3V_XML, L3V_EO_NAME, work)
    assert json_template.lineage_citation(feature) == L3V_XML.name


@pytest.mark.parametrize("entry", [L3_XML, L3V_XML, L1B_XML])
def test_overview_png(tmp_path, entry):
    prod = product_rapideye.Product_Rapideye(str(entry))
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))

    from PIL import Image
    with Image.open(png) as im:
        assert im.format == "PNG"
        assert im.mode == "RGBA"
        assert im.size == (16, 12)
        # the zero (no-data) first column is transparent, the rest opaque
        assert im.getpixel((0, 5))[3] == 0
        assert im.getpixel((8, 5))[3] == 255


def test_browse_preferred_for_overview():
    prod = product_rapideye.Product_Rapideye(str(L3V_XML))
    assert prod.browse_file is not None and prod.browse_file.endswith("_browse.tif")
    assert product_rapideye.Product_Rapideye(str(L3_XML)).browse_file is None


def test_l1b_without_browse_cannot_render_overview(tmp_path):
    folder = tmp_path / "product"
    folder.mkdir()
    for p in L1B_DIR.iterdir():
        if not p.name.endswith("_browse.tif"):
            shutil.copy(p, folder / p.name)
    prod = product_rapideye.Product_Rapideye(str(folder / L1B_XML.name))
    with pytest.raises(Exception, match="no overview source"):
        prod.writeQuicklook(str(tmp_path / "overview.PNG"))


def test_wavelength_table_is_the_specialization_one():
    assert set(product_rapideye.WAVELENGTHS) == {3, 5}
    for bands, ranges in product_rapideye.WAVELENGTHS.items():
        assert sum(len(b) for _, b in ranges) == bands
    allowed = {row[0] for row in product_rapideye.NATIVE_LEVELS.values()}
    assert allowed == {"L1BOPT_MS_", "L3_ORT_MS_"}
    assert all(len(typecode) == 10 for typecode in allowed)


@pytest.mark.parametrize("serial,expected", [
    ("RE-3", "RapidEye-3"), ("RE3", "RapidEye-3"), ("RapidEye-5", "RapidEye-5"),
    ("RE-6", None), ("WV-1", None), (None, None)])
def test_platform_short_name(serial, expected):
    assert product_rapideye.platform_short_name(serial) == expected


def test_satellite_falls_back_on_the_file_name(tmp_path, work):
    entry = _mutated(tmp_path, L3_XML, "<eop:serialIdentifier>RE-1", "<eop:serialIdentifier>unknown")
    _, met = _extract(entry, work)
    assert met.getMetadataValue(product_rapideye.PLATFORM_SHORT_NAME) == "RapidEye-1"


def test_level_falls_back_on_the_file_name(tmp_path, work):
    entry = _mutated(tmp_path, L1B_XML, "<eop:productType>L1B</eop:productType>", "")
    _, met = _extract(entry, work)
    assert met.getMetadataValue(M.METADATA_TYPECODE) == "L1BOPT_MS_"


def test_band_count_falls_back_on_the_image(tmp_path, work):
    entry = _mutated(tmp_path, L3_XML, "<re:numBands>5</re:numBands>", "")
    prod, _ = _extract(entry, work)
    assert prod.num_bands == 5


def test_processing_date_prefers_the_native_element(tmp_path, work):
    entry = _mutated(tmp_path, L3_XML, "<eop:identifier>",
                     "<eop:processingDate>2018-01-02T03:04:05Z</eop:processingDate><eop:identifier>")
    _, met = _extract(entry, work)
    assert met.getMetadataValue(M.METADATA_PROCESSING_TIME) == "2018-01-02T03:04:05.000Z"


def test_pos_list_is_lat_lon():
    from lxml import etree
    node = etree.fromstring("<LinearRing><posList>41 12 41 13 42 13 41 12</posList></LinearRing>")
    assert product_rapideye.parse_ring(node) == [[12.0, 41.0], [13.0, 41.0], [13.0, 42.0], [12.0, 41.0]]


@pytest.mark.parametrize("old,new,message", [
    ("<eop:productType>L3A", "<eop:productType>L2X", "unsupported RapidEye native level"),
    ("<re:numBands>5", "<re:numBands>4", "band count 4 not allowed"),
    ("<eop:orbitDirection>DESCENDING", "<eop:orbitDirection>", "invalid or missing orbit direction"),
    ("<eop:archivingDate>2017-04-25T02:10:33Z</eop:archivingDate>", "", "no processingDate"),
    ('<opt:illuminationAzimuthAngle uom="deg">33.3</opt:illuminationAzimuthAngle>', "", "missing sun azimuth"),
    ("-66.44291264,-24.15261009 -66.44136086", "-666.44291264,-24.15261009 -66.44136086", "out of range"),
])
def test_invalid_metadata_is_rejected(tmp_path, work, old, new, message):
    entry = _mutated(tmp_path, L3_XML, old, new)
    with pytest.raises(Exception, match=message):
        _extract(entry, work)


def test_entry_must_be_product_metadata(tmp_path):
    bogus = tmp_path / "manifest.xml"
    bogus.write_text("<a/>", encoding="utf-8")
    with pytest.raises(Exception, match="not a RapidEye product metadata file"):
        product_rapideye.Product_Rapideye(str(bogus))


def test_wrong_xml_root_is_rejected(tmp_path):
    bogus = tmp_path / "x_metadata.xml"
    bogus.write_text("<a/>", encoding="utf-8")
    with pytest.raises(Exception, match="not a RapidEye metadata XML"):
        product_rapideye.Product_Rapideye(str(bogus))


def test_product_without_image_is_rejected(tmp_path):
    folder = tmp_path / "product"
    folder.mkdir()
    shutil.copy(L3_XML, folder / L3_XML.name)
    with pytest.raises(Exception, match="no RapidEye image"):
        product_rapideye.Product_Rapideye(str(folder / L3_XML.name))


def test_datetime_normalisation():
    norm = product_rapideye.normalise_utc
    assert norm("2021-03-14T07:08:03.311795Z") == "2021-03-14T07:08:03.311Z"
    assert norm("2017-04-24T13:49:11+00:00") == "2017-04-24T13:49:11.000Z"
    assert norm("2017-04-24T15:49:11.5+02:00") == "2017-04-24T13:49:11.500Z"
    assert norm(None) is None


def test_packager_selects_the_same_product_files():
    import importlib
    packager = importlib.import_module("rapideye_json.package_rapideye_zips")
    for stem in (L3_STEM, L3V_STEM):
        prod = product_rapideye.Product_Rapideye(str(DELIVERY_DIR / ("%s_metadata.xml" % stem)))
        assert [str(p) for p in packager.product_files(DELIVERY_DIR, stem)] == prod.files


def test_sar_fields_and_other_missions_absent(work):
    _, _, feature = _feature(L3_XML, L3_EO_NAME, work)
    paths = _key_paths(feature)
    for key in SAR_KEYS:
        assert not any(key in p for p in paths), "SAR field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OTHER_MISSION_TOKENS:
        assert tok not in blob, "other-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path, work):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(L3_XML, work)
    json_emitter.emit(met, prod, L3_EO_NAME, str(out), native_product_name=L3_XML.name)
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % L3_EO_NAME], written
