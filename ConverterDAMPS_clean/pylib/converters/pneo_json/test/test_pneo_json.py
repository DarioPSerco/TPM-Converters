"""Structural proof: drive pneo_json extraction on SYNTHETIC native
Pleiades-NEO deliveries, emit the JSON manifest via the common template
generator, and assert the output matches TDS/template/PLN-template.json
key-path for key-path ("EOPF-EOS Specialization for PLEIADES NEO products"
1.01) - no placeholder left, no Pleiades value leaked in (twin-mission risk).

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
from pneo_json import product_pneo, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_pln"
MS_XML = (FIXTURE_DIR / "DIM_PNEO3_MS_SYNTH.XML").read_text(encoding="utf-8")
LINEAGE_XML = (FIXTURE_DIR / "LINEAGE_SYNTH_DIM.XML").read_bytes()
LINEAGE_NAME = "PROCESSING_PNEO3_202105031049000_SYNTH_DIM.XML"
PLN_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "PLN-template.json"

NATIVE_ZIP_NAME = "SYNTH_PLN_NATIVE_202105031049000.zip"
JOB = "SYNTH_JOB"

PLEIADES_TOKENS = ["HiRI", "PHR1", "Pleiades-1", "PL1_",
                   "EOPF-EOS Converter for PLEIADES\"",
                   "PLEIADES products"]

# spec Table 15 (single component)
PAN_VNIR = {"spectralRange": "VNIR", "startWavelength": 450e-09, "endWavelength": 800e-09,
            "discreteWavelengths": [625e-09]}
MS_VNIR = {"spectralRange": "VNIR", "startWavelength": 400e-09, "endWavelength": 750e-09,
           "discreteWavelengths": [575e-09]}
MS_NIR = {"spectralRange": "NIR", "startWavelength": 770e-09, "endWavelength": 880e-09,
          "discreteWavelengths": [825e-09]}
# spec Table 16 (bundle)
BDL_PAN_VNIR = {"spectralRange": "VNIR", "startWavelength": 480e-09, "endWavelength": 820e-09,
                "discreteWavelengths": [650e-09]}
BDL_MS_NIR = {"spectralRange": "NIR", "startWavelength": 775e-09, "endWavelength": 915e-09,
              "discreteWavelengths": [845e-09]}

LEVEL_XML = {"L1A": "RASTER_SENSOR", "L2": "RASTER_PROJECTED", "L3": "RASTER_ORTHO"}
PROJECTED_CRS = ("<Projected_CRS><PROJECTED_CRS_CODE>urn:ogc:def:crs:EPSG::32719"
                 "</PROJECTED_CRS_CODE></Projected_CRS>")


def _dim_xml(kind, level="L1A"):
    """MS fixture document turned into the given SPECTRAL_PROCESSING kind
    (PAN / MS / PMS ...) and level; PAN / PMS get the 0.3 m resampling
    spacing."""
    xml = MS_XML.replace("_MS_SYNTH", "_%s_SYNTH" % kind)
    xml = xml.replace("<SPECTRAL_PROCESSING>MS<", "<SPECTRAL_PROCESSING>%s<" % kind)
    if not kind.startswith("MS"):
        xml = xml.replace('<RESAMPLING_SPACING unit="m">1.2<', '<RESAMPLING_SPACING unit="m">0.3<')
    xml = xml.replace("RASTER_SENSOR", LEVEL_XML[level])
    if level != "L1A":
        xml = xml.replace("</Coordinate_Reference_System>", PROJECTED_CRS + "</Coordinate_Reference_System>")
    return xml


def _build_native_zip(tmp_path, kinds, level="L1A", lineage=True, edit=None):
    """SYNTHETIC native delivery: one IMG_PNEO3_<kind>_001 folder per
    component with its DIMAP XML, PIL-generated preview JPG, dummy image
    file and LINEAGE document."""
    zip_path = tmp_path / NATIVE_ZIP_NAME
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("%s/VOL_PNEO.XML" % JOB, "<Volume/>")
        for kind in kinds:
            folder = "%s/IMG_PNEO3_%s_001" % (JOB, kind)
            buf = io.BytesIO()
            colour = (200, 200, 200) if kind == "PAN" else (40, 90, 40)
            PIL.Image.new("RGB", (100, 100), colour).save(buf, format="JPEG")
            xml = _dim_xml(kind, level)
            if edit:
                xml = edit(xml)
            zf.writestr("%s/DIM_PNEO3_%s_SYNTH.XML" % (folder, kind), xml)
            zf.writestr("%s/PREVIEW_PNEO3_%s_SYNTH.JPG" % (folder, kind), buf.getvalue())
            zf.writestr("%s/IMG_PNEO3_%s_SYNTH_R1C1.JP2" % (folder, kind), b"synthetic")
            if lineage:
                zf.writestr("%s/LINEAGE/%s" % (folder, LINEAGE_NAME), LINEAGE_XML)
    return zip_path


def _extract(tmp_path, kinds=("MS",), level="L1A", met=None, **kwargs):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path, kinds, level, **kwargs)
    prod = product_pneo.Product_Pneo(str(zip_path))
    prod.extractToPath(str(work))
    met = met or M.Metadata(None)
    prod.extractMetadata(met)
    return prod, met


def _eo_name(met):
    """EO product name as the DDVC naming convention builds it."""
    start = met.getMetadataValue(M.METADATA_START_DATE_TIME)
    stop = met.getMetadataValue(M.METADATA_STOP_DATE_TIME)
    return "PLN_OPER_%s_%s_%s_0001" % (
        met.getMetadataValue(M.METADATA_TYPECODE),
        start[:19].replace("-", "").replace(":", ""),
        stop[:19].replace("-", "").replace(":", ""))


def _feature(tmp_path, kinds=("MS",), level="L1A"):
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


def test_emitted_json_matches_pln_template_structure(tmp_path):
    _, _, _, feature = _feature(tmp_path, kinds=("PAN",))
    json_template.validate(feature)

    with open(PLN_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)

    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_multispectral_primary_values(tmp_path):
    _, _, eo_name, feature = _feature(tmp_path)
    assert json_template.find_placeholders(feature) == []
    assert eo_name == "PLN_OPER_L1APRI_MS__20210503T104900_20210503T105500_0001"
    assert len(eo_name) == len("PLN_OPER_L1APRI_PAN_20210503T104900_20210503T105500_0001")

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
    assert props["date"] == "2021-05-03T10:49:00.806Z/2021-05-03T10:55:00.806Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "Pleiades Neo-3", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "PNEO", "sensorType": "OPTICAL"}

    [par] = acq["acquisitionParameters"]
    assert par["beginningDateTime"] == "2021-05-03T10:49:00.806Z"
    assert par["endingDateTime"] == "2021-05-03T10:55:00.806Z"
    assert par["operationalMode"] == "MS"
    assert par["resolution"] == 1.2
    assert par["acquisitionType"] == "NOMINAL"
    assert par["orbitNumber"] == 56
    assert par["orbitDirection"] == "DESCENDING"
    # the scene center values
    assert par["acquisitionAngles"] == {"incidenceAngle": 20.1,
                                        "illuminationAzimuthAngle": 33.3,
                                        "illuminationElevationAngle": 44.1,
                                        "acrossTrackIncidenceAngle": 0.7,
                                        "alongTrackIncidenceAngle": 20.0}
    assert par["wavelengths"] == [MS_VNIR, MS_NIR]

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1APRI_MS_"
    assert pinfo["processingLevel"] == "L1A"
    assert pinfo["processingDate"] == "2021-05-04T10:12:41.239Z"
    assert pinfo["cloudCover"] == 56.0
    assert "referenceSystemIdentifier" not in pinfo
    assert isinstance(pinfo["size"], int) and pinfo["size"] > 0
    [step] = pinfo["resourceLineage"][0]["processStep"]
    assert step["description"] == "EOPF-EOS Converter for PLEIADES NEO"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["processor"] == [{"role": "processor", "party": [
        {"name": "EOF-EOS External Data Handling", "type": "CI_Organisation"}]}]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for PLEIADES NEO products",
                                  "edition": "1.01"}]
    assert step["source"] == [{"sourceCitation": {"title": NATIVE_ZIP_NAME},
                               "processedLevel": {"code": "L1A"}}]
    assert step["processingInformation"]["softwareReference"]["title"] == "EOPF-EOS Converter for PLEIADES NEO"
    assert step["output"] == [{"sourceCitation": {"title": "%s.ZIP" % eo_name}}]

    links = props["links"]
    assert links["measurements"] == [{
        "href": "/measurements/%s/IMG_PNEO3_MS_001/IMG_PNEO3_MS_SYNTH_R1C1.JP2" % JOB,
        "type": "application/octet-stream", "title": "Native EO Product", "category": "DATA"}]
    assert links["previews"] == [{
        "href": "/previews/overviews/%s.PNG" % eo_name,
        "type": "image/png", "title": "Preview Image", "category": "OVERVIEW"}]


@pytest.mark.parametrize("kinds, level, typecode, modes, wavelengths", [
    (("PAN",), "L1A", "L1APRI_PAN", ["PAN"], [[PAN_VNIR]]),
    (("PAN",), "L2", "L2_PRO_PAN", ["PAN"], [[PAN_VNIR]]),
    (("PAN",), "L3", "L3_ORT_PAN", ["PAN"], [[PAN_VNIR]]),
    (("MS",), "L2", "L2_PRO_MS_", ["MS"], [[MS_VNIR, MS_NIR]]),
    (("MS-FS",), "L3", "L3_ORT_MS_", ["MS"], [[MS_VNIR, MS_NIR]]),
    (("PMS",), "L1A", "L1APRI_PSH", ["MS"], [[PAN_VNIR, MS_VNIR, MS_NIR]]),
    (("PMS-N",), "L2", "L2_PRO_PSH", ["MS"], [[PAN_VNIR, MS_VNIR, MS_NIR]]),
    (("PMS-FS",), "L3", "L3_ORT_PSH", ["MS"], [[PAN_VNIR, MS_VNIR, MS_NIR]]),
    (("PAN", "MS"), "L1A", "L1APRI_BDL", ["MS", "PAN"], [[MS_VNIR, BDL_MS_NIR], [BDL_PAN_VNIR]]),
    (("MS", "PAN"), "L2", "L2_PRO_BDL", ["MS", "PAN"], [[MS_VNIR, BDL_MS_NIR], [BDL_PAN_VNIR]]),
    (("PAN", "MS-FS"), "L3", "L2_ORT_BDL", ["MS", "PAN"], [[MS_VNIR, BDL_MS_NIR], [BDL_PAN_VNIR]]),
])
def test_product_types(tmp_path, kinds, level, typecode, modes, wavelengths):
    _, _, eo_name, feature = _feature(tmp_path, kinds, level)
    json_template.validate(feature)
    pinfo = feature["properties"]["productInformation"]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert pinfo["productType"] == typecode
    assert pinfo["productType"] in product_pneo.PRODUCT_TYPES
    assert eo_name.startswith("PLN_OPER_%s_" % typecode)
    assert pinfo["processingLevel"] == level
    assert pinfo["resourceLineage"][0]["processStep"][0]["source"][0]["processedLevel"]["code"] == level
    assert [p["operationalMode"] for p in pars] == modes
    assert [p["wavelengths"] for p in pars] == wavelengths
    if level == "L1A":
        assert "referenceSystemIdentifier" not in pinfo
    else:
        assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32719"


def test_bundle_links_one_per_component(tmp_path):
    prod, _, eo_name, feature = _feature(tmp_path, kinds=("PAN", "MS"), level="L3")
    links = feature["properties"]["links"]
    assert [m["href"] for m in links["measurements"]] == [
        "/measurements/%s/IMG_PNEO3_MS_001/IMG_PNEO3_MS_SYNTH_R1C1.JP2" % JOB,
        "/measurements/%s/IMG_PNEO3_PAN_001/IMG_PNEO3_PAN_SYNTH_R1C1.JP2" % JOB]
    assert [p["href"] for p in links["previews"]] == [
        "/previews/overviews/%s_MS.PNG" % eo_name,
        "/previews/overviews/%s_PAN.PNG" % eo_name]
    pars = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert [p["resolution"] for p in pars] == [1.2, 0.3]
    assert all(p["acquisitionType"] == "NOMINAL" for p in pars)
    assert all(p["orbitNumber"] == 56 for p in pars)


def test_tiled_image_links_the_dimap_document(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path, ("MS",))
    with zipfile.ZipFile(zip_path) as zf:
        entries = {n: zf.read(n) for n in zf.namelist()}
    dim = "%s/IMG_PNEO3_MS_001/DIM_PNEO3_MS_SYNTH.XML" % JOB
    entries[dim] = entries[dim].replace(
        b"</Data_Files>",
        b'<Data_File tile_R="1" tile_C="2"><DATA_FILE_PATH href="IMG_PNEO3_MS_SYNTH_R1C2.JP2"/>'
        b"</Data_File></Data_Files>")
    entries["%s/IMG_PNEO3_MS_001/IMG_PNEO3_MS_SYNTH_R1C2.JP2" % JOB] = b"synthetic"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    prod = product_pneo.Product_Pneo(str(zip_path))
    prod.extractToPath(str(work))
    met = M.Metadata(None)
    prod.extractMetadata(met)
    assert met.getLocalAttributeValue("measurements") == [{"href": dim, "type": "application/xml"}]


def test_missing_angles_are_left_out(tmp_path):
    _, met = _extract(tmp_path, edit=lambda x: x.replace(
        "<SUN_AZIMUTH unit=\"deg\">33.3</SUN_AZIMUTH>", "").replace(
        "<INCIDENCE_ANGLE>20.1</INCIDENCE_ANGLE>", ""))
    [component] = met.getLocalAttributeValue("components")
    assert "illuminationAzimuthAngle" not in component["angles"]
    assert "incidenceAngle" not in component["angles"]
    assert component["angles"]["illuminationElevationAngle"] == 44.1


def test_orbit_falls_back_to_the_cfg_values(tmp_path):
    met = M.Metadata(None)
    # the base ingester's [Mission-specific-values] cfg injection
    met.setMetadataPair(M.METADATA_ORBIT, "0")
    met.setMetadataPair(M.METADATA_ORBIT_DIRECTION, "DESCENDING")
    _, met = _extract(tmp_path, met=met, lineage=False)
    [component] = met.getLocalAttributeValue("components")
    assert (component["orbitNumber"], component["orbitDirection"]) == (0, "DESCENDING")


def test_no_orbit_anywhere_is_rejected(tmp_path):
    with pytest.raises(Exception, match="orbit"):
        _extract(tmp_path, lineage=False)


def test_platform_neo_4(tmp_path):
    _, met = _extract(tmp_path, edit=lambda x: x.replace(
        "<MISSION_INDEX>3</MISSION_INDEX>", "<MISSION_INDEX>4</MISSION_INDEX>"))
    assert met.getLocalAttributeValue("platformShortName") == "Pleiades Neo-4"
    assert met.getMetadataValue(M.METADATA_PLATFORM_ID) == "N"


@pytest.mark.parametrize("kinds, edit", [
    (("PAN", "PMS"), None),
    (("MS",), lambda x: x.replace("<MISSION_INDEX>3<", "<MISSION_INDEX>1A<")),
    (("MS",), lambda x: x.replace("<CLOUD_COVERAGE>56.0</CLOUD_COVERAGE>", "")),
    (("MS",), lambda x: x.replace("<SPECTRAL_PROCESSING>MS<", "<SPECTRAL_PROCESSING>XS<")),
])
def test_invalid_products_are_rejected(tmp_path, kinds, edit):
    with pytest.raises(Exception):
        _extract(tmp_path, kinds, edit=edit)


def test_overview_pngs(tmp_path):
    prod, _, eo_name, _ = _feature(tmp_path, kinds=("PAN", "MS"))
    out = tmp_path / "out"
    out.mkdir()
    written = prod.writeQuicklooks(str(out), eo_name)
    assert sorted(Path(p).name for p in written) == [
        "%s_MS.PNG" % eo_name, "%s_PAN.PNG" % eo_name]
    for p in written:
        with PIL.Image.open(p) as im:
            assert im.format == "PNG"


def test_datetime_normalisation():
    norm = product_pneo.normalise_utc
    assert norm("2021-05-03T10:49:00.806Z") == "2021-05-03T10:49:00.806Z"
    assert norm("2021-05-04T10:12:41.239") == "2021-05-04T10:12:41.239Z"
    assert norm("2021-05-03T10:49:00.8Z") == "2021-05-03T10:49:00.800Z"
    assert norm("2021-05-03T10:49:00Z") == "2021-05-03T10:49:00.000Z"
    assert norm(None) is None


def test_packager_builds_the_bundle_zip(tmp_path, monkeypatch):
    import importlib
    packager = importlib.import_module("pneo_json.package_pneo_zips")
    outspace, products = tmp_path / "OUTSPACE", tmp_path / "PRODUCTS"
    outspace.mkdir()
    products.mkdir()
    prod, met = _extract(tmp_path, kinds=("PAN", "MS"), level="L3")
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


def test_no_pleiades_values_leaked(tmp_path):
    _, _, _, feature = _feature(tmp_path, kinds=("PAN", "MS"))
    blob = json.dumps(feature)
    for tok in PLEIADES_TOKENS:
        assert tok not in blob, "Pleiades token leaked into PNEO output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(tmp_path)
    eo_name = _eo_name(met)
    json_emitter.emit(met, prod, eo_name, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % eo_name], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
