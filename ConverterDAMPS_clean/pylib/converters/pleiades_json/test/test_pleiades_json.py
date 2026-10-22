"""Structural proof: drive pleiades_json extraction on SYNTHETIC native
Pleiades deliveries, emit the JSON manifest via the common template
generator, and assert the output matches TDS/template/PL1-template.json
key-path for key-path ("EOPF-EOS Specialization for PLEIADES products"
1.01) - no placeholder left, no PNEO value leaked in (twin-mission risk).

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
from pleiades_json import product_pleiades, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_pl1"
MS_XML = (FIXTURE_DIR / "DIM_PHR1A_MS_SYNTH.XML").read_text(encoding="utf-8")
STRIP_XML = (FIXTURE_DIR / "STRIP_DS_SYNTH_DIM.XML").read_bytes()
STRIP_NAME = "STRIP_DS_PHR1A_201704241349118_FR1_PX_W067S25_0224_08756_DIM.XML"
PL1_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "PL1-template.json"

NATIVE_ZIP_NAME = "SYNTH_PL1_NATIVE_201704241349118.zip"
JOB = "SYNTH_JOB"

PNEO_TOKENS = ["PLEIADES NEO", "NEO_", "PNEO", "Pleiades Neo"]

VNIR = {"spectralRange": "VNIR", "startWavelength": 480e-09, "endWavelength": 820e-09,
        "discreteWavelengths": [650e-09]}
VIS = {"spectralRange": "VIS", "startWavelength": 450e-09, "endWavelength": 700e-09,
       "discreteWavelengths": [490e-09, 550e-09, 660e-09]}
NIR = {"spectralRange": "NIR", "startWavelength": 775e-09, "endWavelength": 915e-09,
       "discreteWavelengths": [845e-09]}

LEVEL_XML = {"1A": "RASTER_SENSOR", "2": "RASTER_PROJECTED", "3": "RASTER_ORTHO"}
PROJECTED_CRS = ("<Projected_CRS><PROJECTED_CRS_CODE>urn:ogc:def:crs:EPSG::32719"
                 "</PROJECTED_CRS_CODE></Projected_CRS>")


def _dim_xml(kind, level="1A"):
    """MS fixture document turned into the given kind (P / MS / PMS) and
    level; PAN / PMS get the 0.5 m resampling spacing."""
    xml = MS_XML.replace("_MS_SYNTH", "_%s_SYNTH" % kind)
    xml = xml.replace("<SPECTRAL_PROCESSING>MS<", "<SPECTRAL_PROCESSING>%s<" % kind)
    if kind != "MS":
        xml = xml.replace('<RESAMPLING_SPACING unit="m">2.0<', '<RESAMPLING_SPACING unit="m">0.5<')
    xml = xml.replace("RASTER_SENSOR", LEVEL_XML[level])
    if level != "1A":
        xml = xml.replace("</Coordinate_Reference_System>", PROJECTED_CRS + "</Coordinate_Reference_System>")
    return xml


def _build_native_zip(tmp_path, kinds, level="1A"):
    """SYNTHETIC native delivery: one IMG_PHR1A_<kind>_001 folder per
    component with its DIMAP XML, PIL-generated preview JPG, dummy image
    file and LINEAGE strip document."""
    zip_path = tmp_path / NATIVE_ZIP_NAME
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("%s/VOL_PHR.XML" % JOB, "<Volume/>")
        for kind in kinds:
            folder = "%s/IMG_PHR1A_%s_001" % (JOB, kind)
            buf = io.BytesIO()
            colour = (200, 200, 200) if kind == "P" else (40, 90, 40)
            PIL.Image.new("RGB", (100, 100), colour).save(buf, format="JPEG")
            zf.writestr("%s/DIM_PHR1A_%s_SYNTH.XML" % (folder, kind), _dim_xml(kind, level))
            zf.writestr("%s/PREVIEW_PHR1A_%s_SYNTH.JPG" % (folder, kind), buf.getvalue())
            zf.writestr("%s/IMG_PHR1A_%s_SYNTH_R1C1.JP2" % (folder, kind), b"synthetic")
            zf.writestr("%s/LINEAGE/%s" % (folder, STRIP_NAME), STRIP_XML)
    return zip_path


def _extract(tmp_path, kinds=("MS",), level="1A"):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path, kinds, level)
    prod = product_pleiades.Product_Pleiades(str(zip_path))
    prod.extractToPath(str(work))
    met = M.Metadata(None)
    prod.extractMetadata(met)
    return prod, met


def _eo_name(met):
    """EO product name as the DDVC naming convention builds it."""
    start = met.getMetadataValue(M.METADATA_START_DATE_TIME)
    stop = met.getMetadataValue(M.METADATA_STOP_DATE_TIME)
    return "PL1_OPER_%s_%s_%s_0001" % (
        met.getMetadataValue(M.METADATA_TYPECODE),
        start[:19].replace("-", "").replace(":", ""),
        stop[:19].replace("-", "").replace(":", ""))


def _feature(tmp_path, kinds=("MS",), level="1A"):
    prod, met = _extract(tmp_path, kinds, level)
    eo_name = _eo_name(met)
    mission, dynamic = json_emitter.build_layers(met, prod, eo_name)
    feature = json_template.build(mission, dynamic, template_path=json_emitter.TEMPLATE_PATH)
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


def test_emitted_json_matches_pl1_template_structure(tmp_path):
    _, _, _, feature = _feature(tmp_path, kinds=("P",))
    json_template.validate(feature)

    with open(PL1_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)

    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_multispectral_primary_values(tmp_path):
    _, _, eo_name, feature = _feature(tmp_path)
    assert json_template.find_placeholders(feature) == []
    assert eo_name == "PL1_OPER_L1APRI_MS__20170424T134911_20170424T135006_0001"
    assert len(eo_name) == len("PL1_OPER_L1APRI_MS__20010415T105400_20010415T105500_0001")

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == eo_name
    assert "bbox" not in feature
    assert feature["geometry"]["type"] == "Polygon"
    # counterclockwise, closed, the specialization example's ring
    assert feature["geometry"]["coordinates"] == [[
        [-66.44291264, -24.15261009], [-66.44136086, -24.23036597],
        [-66.36391186, -24.22904374], [-66.36551048, -24.15129263],
        [-66.44291264, -24.15261009]]]
    assert props["status"] == "ACQUIRED"
    assert props["title"] == eo_name
    assert props["date"] == "2017-04-24T13:49:11.806Z/2017-04-24T13:50:06.806Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "Pleiades-1A", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "HiRI", "sensorType": "OPTICAL"}

    [par] = acq["acquisitionParameters"]
    assert par["beginningDateTime"] == "2017-04-24T13:49:11.806Z"
    assert par["endingDateTime"] == "2017-04-24T13:50:06.806Z"
    assert par["operationalMode"] == "MS"
    assert par["resolution"] == 2.0
    assert par["acquisitionType"] == "NOMINAL"
    assert par["orbitNumber"] == 33
    assert par["orbitDirection"] == "ASCENDING"
    # the scene center values
    assert par["acquisitionAngles"] == {"illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "acrossTrackIncidenceAngle": 0.7,
                                        "alongTrackIncidenceAngle": 20.0}
    assert par["wavelengths"] == [VIS, NIR]

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1APRI_MS_"
    assert pinfo["processingLevel"] == "1A"
    assert pinfo["processingDate"] == "2017-04-25T10:12:41.239Z"
    assert "referenceSystemIdentifier" not in pinfo
    assert isinstance(pinfo["size"], int) and pinfo["size"] > 0
    [step] = pinfo["resourceLineage"][0]["processStep"]
    assert step["description"] == "EOPF-EOS Converter for PLEIADES"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for PLEIADES products",
                                  "edition": "1.01"}]
    assert step["source"] == [{"sourceCitation": {"title": NATIVE_ZIP_NAME},
                               "processedLevel": {"code": "L1A"}}]
    assert step["processingInformation"]["softwareReference"]["title"] == "EOPF-EOS Converter for PLEIADES"
    assert step["output"] == [{"sourceCitation": {"title": "%s.ZIP" % eo_name}}]

    links = props["links"]
    assert links["measurements"] == [{
        "href": "/measurements/%s/IMG_PHR1A_MS_001/IMG_PHR1A_MS_SYNTH_R1C1.JP2" % JOB,
        "type": "application/octet-stream", "title": "Native EO Product", "category": "DATA"}]
    assert links["previews"] == [{
        "href": "/previews/overviews/%s.PNG" % eo_name,
        "type": "image/png", "title": "Preview Image", "category": "OVERVIEW"}]


@pytest.mark.parametrize("kinds, level, typecode, modes, wavelengths, processed", [
    (("P",), "1A", "L1APRI_PAN", ["PAN"], [[VNIR]], "L1A"),
    (("P",), "3", "L3_ORT_PAN", ["PAN"], [[VNIR]], "L3"),
    (("MS",), "3", "L3_ORT_MS_", ["MS"], [[VIS, NIR]], "L3"),
    (("PMS",), "1A", "L1APRI_PSH", ["MS"], [[VNIR, VIS, NIR]], "L1A"),
    (("PMS",), "2", "L2_PRO_PSH", ["MS"], [[VNIR, VIS, NIR]], "L2"),
    (("PMS",), "3", "L3_ORT_PSH", ["MS"], [[VNIR, VIS, NIR]], "L3"),
    (("P", "MS"), "1A", "L1APRI_BDL", ["MS", "PAN"], [[VIS, NIR], [VNIR]], "L1A"),
    (("MS", "P"), "2", "L2_PRO_BDL", ["MS", "PAN"], [[VIS, NIR], [VNIR]], "L2"),
    (("P", "MS"), "3", "L3_ORT_BDL", ["MS", "PAN"], [[VIS, NIR], [VNIR]], "L3"),
])
def test_product_types(tmp_path, kinds, level, typecode, modes, wavelengths, processed):
    _, _, eo_name, feature = _feature(tmp_path, kinds, level)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert pinfo["productType"] == typecode
    assert pinfo["productType"] in product_pleiades.PRODUCT_TYPES
    assert pinfo["processingLevel"] == level
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == processed
    assert [p["operationalMode"] for p in pars] == modes
    assert [p["wavelengths"] for p in pars] == wavelengths
    if level == "1A":
        assert "referenceSystemIdentifier" not in pinfo
    else:
        assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"


def test_bundle_links_one_per_component(tmp_path):
    prod, _, eo_name, feature = _feature(tmp_path, kinds=("P", "MS"), level="3")
    links = feature["properties"]["links"]
    assert [m["href"] for m in links["measurements"]] == [
        "/measurements/%s/IMG_PHR1A_MS_001/IMG_PHR1A_MS_SYNTH_R1C1.JP2" % JOB,
        "/measurements/%s/IMG_PHR1A_P_001/IMG_PHR1A_P_SYNTH_R1C1.JP2" % JOB]
    assert [p["href"] for p in links["previews"]] == [
        "/previews/overviews/%s_MS.PNG" % eo_name,
        "/previews/overviews/%s_PAN.PNG" % eo_name]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert [p["resolution"] for p in pars] == [2.0, 0.5]
    assert all(p["acquisitionType"] == "NOMINAL" for p in pars)
    assert all(p["orbitNumber"] == 33 for p in pars)


def test_tiled_image_links_the_dimap_document(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path, ("MS",))
    with zipfile.ZipFile(zip_path) as zf:
        entries = {n: zf.read(n) for n in zf.namelist()}
    dim = "%s/IMG_PHR1A_MS_001/DIM_PHR1A_MS_SYNTH.XML" % JOB
    entries[dim] = entries[dim].replace(
        b"</Data_Files>",
        b'<Data_File tile_R="1" tile_C="2"><DATA_FILE_PATH href="IMG_PHR1A_MS_SYNTH_R1C2.JP2"/>'
        b"</Data_File></Data_Files>")
    entries["%s/IMG_PHR1A_MS_001/IMG_PHR1A_MS_SYNTH_R1C2.JP2" % JOB] = b"synthetic"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    prod = product_pleiades.Product_Pleiades(str(zip_path))
    prod.extractToPath(str(work))
    met = M.Metadata(None)
    prod.extractMetadata(met)
    assert met.getLocalAttributeValue("measurements") == [{"href": dim, "type": "application/xml"}]


def test_missing_angles_are_left_out(tmp_path):
    global MS_XML
    original = MS_XML
    MS_XML = MS_XML.replace("<SUN_AZIMUTH unit=\"deg\">33.3</SUN_AZIMUTH>", "")
    try:
        _, _, _, feature = _feature(tmp_path)
    finally:
        MS_XML = original
    angles = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]["acquisitionAngles"]
    assert "illuminationAzimuthAngle" not in angles
    assert angles["illuminationElevationAngle"] == 44.1


@pytest.mark.parametrize("kinds, level", [(("P",), "2"), (("MS",), "2"), (("P", "PMS"), "1A")])
def test_types_outside_the_specialization_are_rejected(tmp_path, kinds, level):
    with pytest.raises(Exception):
        _extract(tmp_path, kinds, level)


def test_overview_pngs(tmp_path):
    prod, _, eo_name, _ = _feature(tmp_path, kinds=("P", "MS"))
    out = tmp_path / "out"
    out.mkdir()
    written = prod.writeQuicklooks(str(out), eo_name)
    assert sorted(Path(p).name for p in written) == [
        "%s_MS.PNG" % eo_name, "%s_PAN.PNG" % eo_name]
    for p in written:
        with PIL.Image.open(p) as im:
            assert im.format == "PNG"


def test_datetime_normalisation():
    norm = product_pleiades.normalise_utc
    assert norm("2014-03-15T04:54:31.031Z") == "2014-03-15T04:54:31.031Z"
    assert norm("2023-10-05T08:28:31.239") == "2023-10-05T08:28:31.239Z"
    assert norm("2014-03-15T04:54:24.8Z") == "2014-03-15T04:54:24.800Z"
    assert norm("2014-03-15T04:54:24Z") == "2014-03-15T04:54:24.000Z"
    assert norm(None) is None


def test_packager_builds_the_bundle_zip(tmp_path, monkeypatch):
    import importlib
    packager = importlib.import_module("pleiades_json.package_pleiades_zips")
    outspace, products = tmp_path / "OUTSPACE", tmp_path / "PRODUCTS"
    outspace.mkdir()
    products.mkdir()
    prod, met = _extract(tmp_path, kinds=("P", "MS"), level="3")
    eo_name = _eo_name(met)
    json_emitter.emit(met, prod, eo_name, str(outspace))
    prod.writeQuicklooks(str(outspace), eo_name)

    spaces = dict(packager.SPACES, INBOX=tmp_path, OUTSPACE=outspace, PRODUCTS=products,
                  TMPSPACE=tmp_path / "none", DONESPACE=tmp_path / "none")
    monkeypatch.setattr(packager, "SPACES", spaces)
    monkeypatch.setattr(packager, "OUTSPACE", outspace)
    monkeypatch.setattr(packager, "PRODUCTS", products)
    native = packager.package_one(outspace / ("%s.JSON" % eo_name))
    assert native.name == NATIVE_ZIP_NAME

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


def test_no_pneo_values_leaked(tmp_path):
    _, _, _, feature = _feature(tmp_path, kinds=("P", "MS"))
    blob = json.dumps(feature)
    for tok in PNEO_TOKENS:
        assert tok not in blob, "PNEO token leaked into Pleiades output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(tmp_path)
    eo_name = _eo_name(met)
    json_emitter.emit(met, prod, eo_name, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % eo_name], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
