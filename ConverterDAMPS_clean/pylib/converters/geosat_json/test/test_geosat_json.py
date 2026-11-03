"""Structural proof: drive geosat_json extraction on SYNTHETIC native GEOSAT
deliveries, emit the JSON manifest via the common template generator, and
assert the output matches TDS/template/GEOSAT-template.json key-path for
key-path ("EOPF-EOS Specialization for GEOSAT products" 1.01) - no
placeholder left, no PNEO / Pleiades value leaked in.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): this proves
pipeline + structure only, NOT value-correctness on real data.
"""
import io
import json
import zipfile
from pathlib import Path

import PIL.Image
import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from geosat_json import product_geosat, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_geosat"
DE2_XML = (FIXTURE_DIR / "DE2_PAN_L1C_SYNTH.dim").read_text(encoding="utf-8")
DE1_XML = (FIXTURE_DIR / "DE1_SL6_22P_1R_SYNTH.dim").read_text(encoding="utf-8")
GEOSAT_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "GEOSAT-template.json"

DE2_NAME = "DE2_PAN_L1C_000000_20170424T134911_20170424T135006_DE2_15423_7A3F"
DE1_NAME = "DE01_SL6_22P_1R_20170424T134911_20170424T135006_DMI_0_5b2c"

FOREIGN_TOKENS = ["PNEO", "Pleiades", "PLEIADES", "PLN_", "PL1_", "HiRI\""]

# the specialization example's ring, counterclockwise and closed
RING = [[-66.44291264, -24.15261009], [-66.44136086, -24.23036597],
        [-66.36391186, -24.22904374], [-66.36551048, -24.15129263],
        [-66.44291264, -24.15261009]]

# spec Table 16 (and 17)
def _wl(name, start, end):
    return {"spectralRange": name, "startWavelength": start, "endWavelength": end,
            "discreteWavelengths": [round((start + end) / 2, 12)]}


MS3_WL = [_wl("VIS", 520e-09, 600e-09), _wl("VIS", 630e-09, 690e-09), _wl("IR", 770e-09, 900e-09)]
PAN_WL = [_wl("VNIR", 560e-09, 900e-09)]
MS4_WL = [_wl("VIS", 466e-09, 525e-09), _wl("VIS", 532e-09, 599e-09),
          _wl("VIS", 640e-09, 697e-09), _wl("IR", 770e-09, 892e-09)]


def _png():
    buf = io.BytesIO()
    PIL.Image.new("RGB", (120, 80), (90, 120, 60)).save(buf, format="PNG")
    return buf.getvalue()


def _de2_name(mode, level="1C"):
    return DE2_NAME.replace("DE2_PAN_L1C", "DE2_%s_L%s" % (mode, level))


def _de2_xml(mode, level="1C", images=None):
    """PAN L1C fixture document turned into the given mode / level; images:
    the Data_File list (default: the document's own .tif)."""
    name = _de2_name(mode, level)
    xml = DE2_XML.replace(DE2_NAME, name)
    xml = xml.replace("<PRODUCT_TYPE>L1C<", "<PRODUCT_TYPE>L%s<" % level)
    if images is not None:
        files = "".join('<Data_File><DATA_FILE_PATH href="%s"/></Data_File>' % i for i in images)
        start = xml.index("<Data_File>")
        end = xml.rindex("</Data_File>") + len("</Data_File>")
        xml = xml[:start] + files + xml[end:]
    return xml


def _write_zip(zip_path, entries):
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return zip_path


def _de2_entries(mode, level="1C", edit=None, folder=None):
    name = _de2_name(mode, level)
    folder = folder or name
    xml = _de2_xml(mode, level)
    if edit:
        xml = edit(xml)
    return {"%s/%s.dim" % (folder, name): xml,
            "%s/%s.tif" % (folder, name): b"synthetic",
            "%s/%s_QL.png" % (folder, name): _png()}


def _build_zip(tmp_path, entries, zip_name):
    return _write_zip(tmp_path / zip_name, entries)


def _extract_zip(tmp_path, zip_path, met=None):
    work = tmp_path / "work"
    work.mkdir()
    prod = product_geosat.Product_Geosat(str(zip_path))
    prod.extractToPath(str(work))
    met = met or M.Metadata(None)
    prod.extractMetadata(met)
    return prod, met


def _extract(tmp_path, mode="PAN", level="1C", edit=None, met=None):
    zip_path = _build_zip(tmp_path, _de2_entries(mode, level, edit), "%s.zip" % _de2_name(mode, level))
    return _extract_zip(tmp_path, zip_path, met)


def _extract_de1(tmp_path, level="1R", edit=None, orbit="0"):
    name = DE1_NAME.replace("_1R_", "_%s_" % level)
    xml = DE1_XML.replace(DE1_NAME, name).replace("<PRODUCT_TYPE>L1R<", "<PRODUCT_TYPE>L%s<" % level)
    if edit:
        xml = edit(xml)
    entries = {"%s/%s.dim" % (name, name): xml, "%s/%s.tif" % (name, name): b"synthetic",
               "%s/%s_QL.png" % (name, name): _png()}
    met = M.Metadata(None)
    if orbit is not None:
        # the base ingester's [Mission-specific-values] cfg injection
        met.setMetadataPair(M.METADATA_ORBIT, orbit)
    return _extract_zip(tmp_path, _build_zip(tmp_path, entries, "%s.zip" % name), met)


def _eo_name(met):
    """EO product name as the DDVC naming convention builds it."""
    start = met.getMetadataValue(M.METADATA_START_DATE_TIME)
    stop = met.getMetadataValue(M.METADATA_STOP_DATE_TIME)
    return "DE%s_OPER_%s_%s_%s_0001" % (
        met.getMetadataValue(M.METADATA_PLATFORM_ID),
        met.getMetadataValue(M.METADATA_TYPECODE),
        start[:19].replace("-", "").replace(":", ""),
        stop[:19].replace("-", "").replace(":", ""))


def _feature_of(prod, met):
    eo_name = _eo_name(met)
    mission, dynamic = json_emitter.build_layers(met, prod, eo_name)
    feature = json_template.build(mission, dynamic, template_path=json_emitter.TEMPLATE_PATH)
    return eo_name, feature


def _feature(tmp_path, mode="PAN", level="1C"):
    prod, met = _extract(tmp_path, mode, level)
    eo_name, feature = _feature_of(prod, met)
    return prod, met, eo_name, feature


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


def test_emitted_json_matches_geosat_template_structure(tmp_path):
    _, _, _, feature = _feature(tmp_path)
    json_template.validate(feature)
    with open(GEOSAT_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_geosat2_panchromatic_values(tmp_path):
    _, _, eo_name, feature = _feature(tmp_path)
    assert json_template.find_placeholders(feature) == []
    assert eo_name == "DE2_OPER_L1CORT_PAN_20170424T134911_20170424T135006_0001"
    assert len(eo_name) == len("DE1_OPER_L1CORT_PAN_20170424T134911_20170424T135111_0001")

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == eo_name
    assert feature["geometry"] == {"type": "Polygon", "coordinates": [RING]}
    assert props["status"] == "ACQUIRED"
    assert props["title"] == eo_name
    assert props["date"] == "2017-04-24T13:49:11.806Z/2017-04-24T13:50:06.806Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "GEOSAT-2", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "HiRAIS", "sensorType": "OPTICAL"}

    [par] = acq["acquisitionParameters"]
    assert par == {
        "beginningDateTime": "2017-04-24T13:49:11.806Z",
        "endingDateTime": "2017-04-24T13:50:06.806Z",
        "operationalMode": "PAN",
        "resolution": 0.75,
        "acquisitionType": "NOMINAL",
        "orbitNumber": 15423,
        "orbitDirection": "ASCENDING",
        "acquisitionAngles": {"illuminationAzimuthAngle": 33.3,
                              "illuminationElevationAngle": 44.1,
                              "incidenceAngle": 12.5},
        "wavelengths": PAN_WL,
    }

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1CORT_PAN"
    assert pinfo["processingLevel"] == "L1C"
    assert pinfo["processingDate"] == "2017-04-25T08:12:41.239Z"
    assert pinfo["cloudCover"] == 12.5
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"
    assert isinstance(pinfo["size"], int) and pinfo["size"] > 0
    [step] = pinfo["resourceLineage"][0]["processStep"]
    assert step["description"] == "GEOSAT processor"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for GEOSAT products",
                                  "edition": "1.01"}]
    assert step["source"] == [{"sourceCitation": {"title": "%s.zip" % _de2_name("PAN")},
                               "processedLevel": {"code": "L1C"}}]
    assert step["processingInformation"]["softwareReference"]["title"] == "EOPF-EOS Converter for GEOSAT"
    assert step["output"] == [{"sourceCitation": {"title": eo_name}}]

    links = props["links"]
    assert links["measurements"] == [{
        "href": "/measurements/%s/%s.tif" % (DE2_NAME, DE2_NAME),
        "type": "image/tiff", "title": "Native EO Product", "category": "DATA"}]
    assert links["previews"] == [{
        "href": "/previews/overviews/%s.PNG" % eo_name,
        "type": "image/png", "title": "Preview Image", "category": "OVERVIEW"}]


def test_geosat1_geopositioned_values(tmp_path):
    prod, met = _extract_de1(tmp_path)
    eo_name, feature = _feature_of(prod, met)
    json_template.validate(feature)
    assert eo_name == "DE1_OPER_L1_GEO_MS__20170424T134911_20170424T135006_0001"
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    assert acq["platform"] == {"platformShortName": "GEOSAT-1", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "SLIM6", "sensorType": "OPTICAL"}
    [par] = acq["acquisitionParameters"]
    assert par["operationalMode"] == "MS3B"
    assert par["resolution"] == 22.0
    assert par["orbitNumber"] == 0
    assert par["orbitDirection"] == "ASCENDING"
    assert par["beginningDateTime"] == "2017-04-24T13:49:11.000Z"
    # the specialization's L1_GEO_MS_ example rows: 560 / 660 / 835 nm
    assert par["wavelengths"] == MS3_WL
    assert [w["discreteWavelengths"] for w in par["wavelengths"]] == [[560e-09], [660e-09], [835e-09]]
    assert feature["geometry"]["coordinates"] == [RING]
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1_GEO_MS_"
    assert pinfo["processingLevel"] == "L1"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert "cloudCover" not in pinfo
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1"


@pytest.mark.parametrize("level, typecode, processing, code", [
    ("1R", "L1_GEO_MS_", "L1", "L1"),
    ("1T", "L1_ORT_MS_", "L1", "L1"),
    ("2T", "L2_ORT_MS_", "L2", "L2T"),
])
def test_geosat1_product_types(tmp_path, level, typecode, processing, code):
    prod, met = _extract_de1(tmp_path, level)
    _, feature = _feature_of(prod, met)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    assert (pinfo["productType"], pinfo["processingLevel"]) == (typecode, processing)
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == code


def test_geosat1_without_orbit_direction_leaves_it_out(tmp_path):
    prod, met = _extract_de1(tmp_path, edit=lambda x: x.replace("SPACEMETRIC:HEADING", "OTHER:CODE"))
    _, feature = _feature_of(prod, met)
    [par] = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert "orbitDirection" not in par


@pytest.mark.parametrize("mode, level, typecode, opmode, processing, resolution, wl", [
    ("PAN", "1B", "L1BORTRPAN", "PAN", "L1B", 0.75, PAN_WL),
    ("PAN", "1C", "L1CORT_PAN", "PAN", "L1C", 0.75, PAN_WL),
    ("MS4", "1B", "L1BORTRMS_", "MS4B", "L1B", 0.75, MS4_WL),
    ("MS4", "1C", "L1CORT_MS_", "MS4B", "L1C", 0.75, MS4_WL),
    ("PSH", "1B", "L1BORTRPSH", "MS4B", "L1B", 0.75, MS4_WL),
    ("PSH", "1C", "L1CORT_PSH", "MS4B", "L1C", 0.75, MS4_WL),
    ("PS4", "1D", "L1DORTEPSH", "MS4B", "L1D", 0.75, MS4_WL),
])
def test_geosat2_product_types(tmp_path, mode, level, typecode, opmode, processing, resolution, wl):
    _, met, eo_name, feature = _feature(tmp_path, mode, level)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    [par] = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert pinfo["productType"] == typecode
    assert eo_name.startswith("DE2_OPER_%s_" % typecode)
    assert pinfo["processingLevel"] == processing
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == processing
    assert par["operationalMode"] == opmode
    assert par["resolution"] == resolution
    assert par["wavelengths"] == wl


def test_resolution_falls_back_to_the_nominal_value(tmp_path):
    _, met = _extract(tmp_path, "MS4", "1C", edit=lambda x: x.replace(
        "<PIXEL_RESOLUTION_X>0.75</PIXEL_RESOLUTION_X>", "").replace(
        "<THEORETICAL_RESOLUTION>1.0</THEORETICAL_RESOLUTION>", ""))
    [component] = met.getLocalAttributeValue("components")
    assert component["resolution"] == 3.0


def _bundle_entries(level="1C"):
    entries = {}
    for mode in ("PAN", "MS4"):
        entries.update(_de2_entries(mode, level, folder="BUNDLE"))
    return entries


@pytest.mark.parametrize("level, typecode", [
    ("1B", "L1BORTRBDL"), ("1C", "L1CORT_BDL"), ("1D", "L1DORTEBDL")])
def test_bundle_two_documents(tmp_path, level, typecode):
    zip_path = _build_zip(tmp_path, _bundle_entries(level), "%s.zip" % _de2_name("PM4", level))
    prod, met = _extract_zip(tmp_path, zip_path)
    eo_name, feature = _feature_of(prod, met)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert pinfo["productType"] == typecode
    assert pinfo["processingLevel"] == "L%s" % level
    # the bundle example: two entries, MS first, both operationalMode MS
    assert [p["operationalMode"] for p in pars] == ["MS", "MS"]
    assert [p["wavelengths"] for p in pars] == [MS4_WL, PAN_WL]
    links = feature["properties"]["links"]
    assert [m["href"] for m in links["measurements"]] == [
        "/measurements/BUNDLE/%s.tif" % _de2_name("MS4", level),
        "/measurements/BUNDLE/%s.tif" % _de2_name("PAN", level)]
    assert [p["href"] for p in links["previews"]] == [
        "/previews/overviews/%s_MS.PNG" % eo_name, "/previews/overviews/%s_PAN.PNG" % eo_name]


def test_bundle_one_document_split_by_image(tmp_path):
    folder = _de2_name("PM4")
    images = ["%s.tif" % _de2_name("PAN"), "%s.tif" % _de2_name("MS4")]
    entries = {"%s/%s.dim" % (folder, folder): _de2_xml("PM4", images=images)}
    for image in images:
        entries["%s/%s" % (folder, image)] = b"synthetic"
        entries["%s/%s_QL.png" % (folder, image[:-4])] = _png()
    prod, met = _extract_zip(tmp_path, _build_zip(tmp_path, entries, "%s.zip" % folder))
    eo_name, feature = _feature_of(prod, met)
    json_template.validate(feature)
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert feature["properties"]["productInformation"]["productType"] == "L1CORT_BDL"
    # one document for both: the nominal resolution of each component
    assert [p["resolution"] for p in pars] == [3.0, 0.75]
    assert [c["preview"] for c in prod.components] == [
        "%s/%s_QL.png" % (folder, _de2_name("MS4")), "%s/%s_QL.png" % (folder, _de2_name("PAN"))]


@pytest.mark.parametrize("mode, typecode, opmode", [
    ("PAN", "SYNSTERPAN", "PAN"), ("PSH", "SYNSTERPSH", "MS")])
def test_stereo_pair(tmp_path, mode, typecode, opmode):
    entries = {}
    entries.update(_de2_entries(mode, "1B", folder="VIEW_1"))
    entries.update(_de2_entries(mode, "1B", folder="VIEW_2", edit=lambda x: x.replace(
        "13:50:06.806", "13:50:30.000")))
    prod, met = _extract_zip(tmp_path, _build_zip(tmp_path, entries, "%s.zip" % _de2_name("STP", "1B")))
    eo_name, feature = _feature_of(prod, met)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert pinfo["productType"] == typecode
    assert pinfo["processingLevel"] == "SYN"
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == "L1B"
    assert [p["operationalMode"] for p in pars] == [opmode, opmode]
    assert feature["properties"]["date"].endswith("/2017-04-24T13:50:30.000Z")
    assert [p["href"] for p in feature["properties"]["links"]["previews"]] == [
        "/previews/overviews/%s_1.PNG" % eo_name, "/previews/overviews/%s_2.PNG" % eo_name]


def test_tiled_image_links_the_dimap_document(tmp_path):
    name = _de2_name("PAN")
    tiles = ["%s_R1C1.tif" % name, "%s_R1C2.tif" % name]
    entries = {"%s/%s.dim" % (name, name): _de2_xml("PAN", images=tiles),
               "%s/%s_QL.png" % (name, name): _png()}
    for tile in tiles:
        entries["%s/%s" % (name, tile)] = b"synthetic"
    _, met = _extract_zip(tmp_path, _build_zip(tmp_path, entries, "%s.zip" % name))
    assert met.getLocalAttributeValue("measurements") == [
        {"href": "%s/%s.dim" % (name, name), "type": "application/xml"}]


def test_missing_optional_values_are_left_out(tmp_path):
    _, met = _extract(tmp_path, edit=lambda x: x.replace(
        "<SUN_AZIMUTH>33.3</SUN_AZIMUTH>", "").replace(
        "<INCIDENCE_ANGLE>12.5</INCIDENCE_ANGLE>", "").replace(
        "GEOSAT:CCP", "OTHER:CODE").replace(
        "<HORIZONTAL_CS_CODE>EPSG:32719</HORIZONTAL_CS_CODE>", ""),
        level="1B")
    [component] = met.getLocalAttributeValue("components")
    assert component["angles"] == {"illuminationElevationAngle": 44.1}
    assert not met.valueExists(met.getMetadataValue(M.METADATA_CLOUD_COVERAGE))
    # L1B: ortho ready, not geo-referenced, no CRS required
    assert met.getLocalAttributeValue("referenceSystemIdentifier") is None


def test_negative_cloud_cover_is_left_out(tmp_path):
    _, met = _extract(tmp_path, edit=lambda x: x.replace("<QUALITY_PARAMETER_VALUE>12.5<",
                                                         "<QUALITY_PARAMETER_VALUE>-1<"))
    assert not met.valueExists(met.getMetadataValue(M.METADATA_CLOUD_COVERAGE))


def test_orbit_from_the_document_wins(tmp_path):
    _, met = _extract(tmp_path, edit=lambda x: x.replace(
        "</Scene_Source>", "<ORBIT_NUMBER>777</ORBIT_NUMBER></Scene_Source>"))
    [component] = met.getLocalAttributeValue("components")
    assert component["orbitNumber"] == 777


def test_no_orbit_anywhere_is_rejected(tmp_path):
    with pytest.raises(Exception, match="orbit"):
        _extract_de1(tmp_path, orbit=None)


@pytest.mark.parametrize("mode, level, edit", [
    ("PAN", "1C", lambda x: x.replace("GEOSAT:ORD", "OTHER:CODE")),            # GEOSAT-2 needs the direction
    ("PAN", "1C", lambda x: x.replace(">ASCENDING<", ">SIDEWAYS<")),
    ("PAN", "1C", lambda x: x.replace("<HORIZONTAL_CS_CODE>EPSG:32719</HORIZONTAL_CS_CODE>", "")),  # ortho, no CRS
    ("PAN", "1C", lambda x: x.replace("<PRODUCT_TYPE>L1C<", "<PRODUCT_TYPE>L1B<")),
    ("PAN", "1C", lambda x: x.replace("<MISSION_INDEX>2<", "<MISSION_INDEX>1<")),
    ("PAN", "1D", None),                                                        # no L1D PAN type
    ("PS3", "1C", None),                                                        # 3-band PSH: no type
    ("PAN", "1C", lambda x: x.replace("<DATASET_PRODUCTION_DATE>2017-04-25T08:12:41.239</DATASET_PRODUCTION_DATE>", "")),
])
def test_invalid_products_are_rejected(tmp_path, mode, level, edit):
    with pytest.raises(Exception):
        _extract(tmp_path, mode, level, edit=edit)


def test_pan_plus_psh_is_not_a_bundle(tmp_path):
    entries = {}
    entries.update(_de2_entries("PAN", folder="A"))
    entries.update(_de2_entries("PSH", folder="B"))
    with pytest.raises(Exception, match="component set"):
        _extract_zip(tmp_path, _build_zip(tmp_path, entries, "mixed.zip"))


def test_overview_pngs(tmp_path):
    zip_path = _build_zip(tmp_path, _bundle_entries(), "%s.zip" % _de2_name("PM4"))
    prod, met = _extract_zip(tmp_path, zip_path)
    eo_name = _eo_name(met)
    out = tmp_path / "out"
    out.mkdir()
    written = prod.writeQuicklooks(str(out), eo_name)
    assert sorted(Path(p).name for p in written) == ["%s_MS.PNG" % eo_name, "%s_PAN.PNG" % eo_name]
    for p in written:
        with PIL.Image.open(p) as im:
            assert im.format == "PNG"


def test_overview_from_the_image_without_quicklook(tmp_path):
    name = _de2_name("PAN")
    buf = io.BytesIO()
    PIL.Image.new("L", (300, 200), 128).save(buf, format="TIFF")
    entries = {"%s/%s.dim" % (name, name): _de2_xml("PAN").replace(
                   '<DATASET_QL_PATH href="%s_QL.png"/>' % name, ""),
               "%s/%s.tif" % (name, name): buf.getvalue()}
    prod, met = _extract_zip(tmp_path, _build_zip(tmp_path, entries, "%s.zip" % name))
    out = tmp_path / "out"
    out.mkdir()
    [written] = prod.writeQuicklooks(str(out), _eo_name(met))
    with PIL.Image.open(written) as im:
        assert im.format == "PNG" and im.size == (300, 200)


def test_datetime_normalisation():
    norm = product_geosat.normalise_utc
    assert norm("2017-04-24T13:49:11.806Z") == "2017-04-24T13:49:11.806Z"
    assert norm("2017-04-24T13:49:11.806") == "2017-04-24T13:49:11.806Z"
    assert norm("2017-04-24 13:49:11") == "2017-04-24T13:49:11.000Z"
    assert norm("2017-04-24T13:49:11.8+00:00") == "2017-04-24T13:49:11.800Z"
    assert norm(None) is None
    with pytest.raises(Exception):
        norm("24/04/2017")


def test_crs_from_wkt():
    wkt = ('PROJCS["WGS 84 / UTM zone 19S",GEOGCS["WGS 84",AUTHORITY["EPSG","4326"]],'
           'AUTHORITY["EPSG","32719"]]')
    assert product_geosat.crs_uri(product_geosat.wkt_epsg(wkt)) == "http://www.opengis.net/def/crs/EPSG/0/32719"
    assert product_geosat.crs_uri("urn:ogc:def:crs:EPSG::4326") == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert product_geosat.crs_uri("not a crs") is None


def test_packager_builds_the_bundle_zip(tmp_path, monkeypatch):
    import importlib
    packager = importlib.import_module("geosat_json.package_geosat_zips")
    outspace, products = tmp_path / "OUTSPACE", tmp_path / "PRODUCTS"
    outspace.mkdir()
    products.mkdir()
    zip_path = _build_zip(tmp_path, _bundle_entries(), "%s.zip" % _de2_name("PM4"))
    prod, met = _extract_zip(tmp_path, zip_path)
    eo_name = _eo_name(met)
    json_emitter.emit(met, prod, eo_name, str(outspace))
    prod.writeQuicklooks(str(outspace), eo_name)

    spaces = dict(packager.SPACES, INBOX=tmp_path, OUTSPACE=outspace, PRODUCTS=products,
                  TMPSPACE=tmp_path / "none", DONESPACE=tmp_path / "none")
    monkeypatch.setattr(packager, "SPACES", spaces)
    monkeypatch.setattr(packager, "OUTSPACE", outspace)
    monkeypatch.setattr(packager, "PRODUCTS", products)
    native = packager.package_one(outspace / ("%s.JSON" % eo_name))
    assert native.name == zip_path.name

    with zipfile.ZipFile(products / ("%s.ZIP" % eo_name)) as zf:
        names = set(zf.namelist())
        assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())
    with zipfile.ZipFile(native) as zf:
        native_names = {"measurements/%s" % n for n in zf.namelist()}
    assert "%s.JSON" % eo_name in names
    assert {"previews/overviews/%s_MS.PNG" % eo_name,
            "previews/overviews/%s_PAN.PNG" % eo_name} <= names
    assert native_names <= names
    assert len(names) == 1 + 2 + len(native_names)


def test_no_foreign_mission_values_leaked(tmp_path):
    _, _, _, feature = _feature(tmp_path)
    blob = json.dumps(feature)
    for tok in FOREIGN_TOKENS:
        assert tok not in blob, "foreign token leaked into GEOSAT output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(tmp_path)
    eo_name = _eo_name(met)
    json_emitter.emit(met, prod, eo_name, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % eo_name], written
