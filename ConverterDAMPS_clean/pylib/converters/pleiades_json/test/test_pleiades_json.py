"""Structural proof: drive pleiades_json extraction on a SYNTHETIC native
Pleiades package, emit the JSON manifest via the common template generator,
and assert the output matches TDS/template/PL1-template.json key-path for
key-path — Airbus-DIMAP fields present, no placeholder left, no PNEO value
leaked in (twin-mission risk).

Fixture is SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): this proves
pipeline + structure only, NOT value-correctness on real data (PENDING TDS).
"""
import io
import json
import zipfile
from pathlib import Path

import PIL.Image

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from pleiades_json import product_pleiades, json_emitter

FIXTURE_XML = Path(__file__).resolve().parent / "fixtures" / "synthetic_pl1" / "DIM_PHR1A_MS_SYNTH.XML"
PL1_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "PL1-template.json"

NATIVE_ZIP_NAME = "SYNTH_PL1_NATIVE_201605011446068.zip"
EO_PRODUCT_NAME = "PL1_OPER_HIR_MS__1A_20160501T144600_S24-190_W066-403_0301"

PNEO_TOKENS = ["PLEIADES NEO", "NEO_", "PNEO", "Pleiades Neo"]


class _InfoKeeperStub:
    def addInfo(self, *args, **kwargs):
        pass


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder
        self.infoKeeper = _InfoKeeperStub()

    def addLog(self, *args, **kwargs):
        pass


def _build_native_zip(tmp_path):
    """SYNTHETIC native package: DIMAP XML + PIL-generated preview JPG +
    dummy IMG_PHR1 raster entry (isPleiades flag)."""
    zip_path = tmp_path / NATIVE_ZIP_NAME
    buf = io.BytesIO()
    PIL.Image.new("RGB", (100, 100), (40, 90, 40)).save(buf, format="JPEG")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SYNTH_PL1_PRODUCT/DIM_PHR1A_MS_SYNTH.XML", FIXTURE_XML.read_bytes())
        zf.writestr("SYNTH_PL1_PRODUCT/PREVIEW_PHR1A_MS_SYNTH.JPG", buf.getvalue())
        zf.writestr("SYNTH_PL1_PRODUCT/IMG_PHR1A_MS_001/IMG_PHR1A_R1C1.TIF", b"synthetic")
    return zip_path


def _extract(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path)
    prod = product_pleiades.Product_Pleiades(str(zip_path))
    prod.processInfo = _ProcessInfoStub(str(work))
    prod.extractToPath(str(work))
    met = M.Metadata(None)
    # simulate the base ingester's [Mission-specific-values] cfg injection
    met.setMetadataPair(M.METADATA_SENSOR_NAME, "HIR")
    met.setMetadataPair(M.METADATA_ORBIT, "0")
    met.setMetadataPair(M.METADATA_ORBIT_DIRECTION, "DESCENDING")
    met.setMetadataPair(M.METADATA_FILECOUNTER, "1")
    prod.extractMetadata(met)
    # simulate ingester_pleiades.beforeReportsDone: full trailing-_ strip
    mode = met.getMetadataValue(M.METADATA_SENSOR_OPERATIONAL_MODE)
    while mode.endswith("_"):
        mode = mode[0:-1]
    met.setMetadataPair(M.METADATA_SENSOR_OPERATIONAL_MODE, mode)
    return prod, met


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
    prod, met = _extract(tmp_path)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    json_template.validate(feature)

    with open(PL1_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)

    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_mission_values_present_and_no_placeholder(tmp_path):
    prod, met = _extract(tmp_path)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"]
    par = acq["acquisitionParameters"]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert len(feature["bbox"]) == 4
    assert feature["bbox"][0] < feature["bbox"][2]
    assert feature["bbox"][1] < feature["bbox"][3]
    assert props["status"] == "ARCHIVED"
    assert acq["platform"]["platformShortName"] == "PLEIADES"
    assert acq["platform"]["platformSerialIdentifier"] == "1A"
    assert acq["platform"]["orbitType"] == "LEO"
    assert acq["instrument"]["instrumentShortName"] == "HiRI"
    assert acq["instrument"]["sensorType"] == "OPTICAL"
    assert par["operationalMode"] == "MS"
    assert par["orbitNumber"] == 0
    assert par["orbitDirection"] == "DESCENDING"
    assert par["wrsLongitudeGrid"] == "W066"
    assert par["wrsLatitudeGrid"] == "S24"
    assert par["acquisitionType"] == "NOMINAL"
    angles = par["acquisitionAngles"]
    assert angles["illuminationAzimuthAngle"] == 145.23
    assert angles["illuminationElevationAngle"] == 61.74
    assert angles["acrossTrackIncidenceAngle"] == 7.18
    assert angles["alongTrackIncidenceAngle"] == 5.32
    assert par["beginningDateTime"] == "2016-05-01T14:46:00.000Z"
    assert par["endingDateTime"] == par["beginningDateTime"]
    assert props["created"] == "2021-02-01T15:30:23.000Z"
    assert props["productInformation"]["productType"] == "HIR_MS__1A"
    assert isinstance(props["productInformation"]["size"], int)
    assert props["productInformation"]["size"] > 0
    lineage = props["productInformation"]["resourceLineage"]["processStep"]
    assert lineage["description"] == "EOPF-EOS Converter for PLEIADES"
    assert lineage["reference"]["title"] == "EOPF-EOS Specialization for PLEIADES products"
    assert lineage["source"]["citation"] == NATIVE_ZIP_NAME
    assert lineage["source"]["processedLevel"] == "1A"
    assert lineage["output"]["sourceCitation"]["title"] == "%s.ZIP" % EO_PRODUCT_NAME


def test_no_pneo_values_leaked(tmp_path):
    prod, met = _extract(tmp_path)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    blob = json.dumps(feature)
    for tok in PNEO_TOKENS:
        assert tok not in blob, "PNEO token leaked into Pleiades output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(tmp_path)
    json_emitter.emit(met, prod, EO_PRODUCT_NAME, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % EO_PRODUCT_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
