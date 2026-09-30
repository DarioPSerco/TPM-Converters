"""Structural proof: drive pneo_json extraction on a SYNTHETIC native
Pleiades-NEO package, emit the JSON manifest via the common template
generator, and assert the output matches TDS/template/PLN-template.json
key-path for key-path — Airbus-DIMAP fields present, no placeholder left,
no Pleiades value leaked in (twin-mission risk).

CAVEAT: the fixture's Solar_Incidences block uses the same [INFERRED from
Pleiades DIMAP layout] paths the new xmlMapping entries expect, so these
tests prove nothing about those paths existing in real PNEO DIMAP — top
PENDING item (see fixtures/SYNTHETIC_FIXTURE_NOTE.md).

Fixture is SYNTHETIC: pipeline + structure only, NOT value-correctness on
real data (PENDING TDS).
"""
import io
import json
import zipfile
from pathlib import Path

import PIL.Image

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from pneo_json import product_pneo, json_emitter

FIXTURE_XML = Path(__file__).resolve().parent / "fixtures" / "synthetic_pln" / "DIM_PNEO1_MS_SYNTH.XML"
PLN_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "PLN-template.json"

NATIVE_ZIP_NAME = "SYNTH_PLN_NATIVE_202105031049000.zip"
EO_PRODUCT_NAME = "PLN_OPER_NEO_MS__2__20210503T104900_N41-376_E002-153_01"

PLEIADES_TOKENS = ["HIR_", "PHR1", '"PLEIADES"',
                   "EOPF-EOS Converter for PLEIADES\"",
                   "PLEIADES products"]


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
    dummy IMG_PNEO raster entry (isPneo flag)."""
    zip_path = tmp_path / NATIVE_ZIP_NAME
    buf = io.BytesIO()
    PIL.Image.new("RGB", (100, 100), (40, 60, 110)).save(buf, format="JPEG")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("SYNTH_PLN_PRODUCT/DIM_PNEO1_MS_SYNTH.XML", FIXTURE_XML.read_bytes())
        zf.writestr("SYNTH_PLN_PRODUCT/PREVIEW_PNEO1_MS_SYNTH.JPG", buf.getvalue())
        zf.writestr("SYNTH_PLN_PRODUCT/IMG_PNEO1_MS_001/IMG_PNEO1_202105031049000_MS_2__MS_R1C1.JP2",
                    b"synthetic")
    return zip_path


def _extract(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    zip_path = _build_native_zip(tmp_path)
    prod = product_pneo.Product_Pneo(str(zip_path))
    prod.processInfo = _ProcessInfoStub(str(work))
    prod.extractToPath(str(work))
    met = M.Metadata(None)
    # simulate the base ingester's [Mission-specific-values] cfg injection
    met.setMetadataPair(M.METADATA_SENSOR_NAME, "NEO")
    met.setMetadataPair(M.METADATA_ORBIT, "0")
    met.setMetadataPair(M.METADATA_ORBIT_DIRECTION, "DESCENDING")
    met.setMetadataPair(M.METADATA_FILECOUNTER, "1")
    prod.extractMetadata(met)
    # simulate ingester_pneo.beforeReportsDone: trailing-_ strip WITH the
    # len-3 guard (suspected pipeline bug, kept unchanged: 'MS_' stays 'MS_')
    mode = met.getMetadataValue(M.METADATA_SENSOR_OPERATIONAL_MODE)
    while mode.endswith("_"):
        if len(mode) == 3:
            break
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


def test_emitted_json_matches_pln_template_structure(tmp_path):
    prod, met = _extract(tmp_path)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    json_template.validate(feature)

    with open(PLN_TEMPLATE, encoding="utf-8") as fd:
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
    assert acq["platform"]["platformShortName"] == "PLEIADES NEO"
    assert acq["platform"]["platformSerialIdentifier"] == "3"
    assert acq["platform"]["orbitType"] == "LEO"
    # per the PLN template (the ONLY structural reference) - suspected
    # wrong for PNEO, see PENDING in PLEIADES_PNEO_DEV.md
    assert acq["instrument"]["instrumentShortName"] == "HiRI"
    assert acq["instrument"]["sensorType"] == "OPTICAL"
    # len-3 guard keeps the padding underscore (pipeline behaviour, flagged)
    assert par["operationalMode"] == "MS_"
    assert par["orbitNumber"] == 0
    assert par["orbitDirection"] == "DESCENDING"
    assert par["wrsLongitudeGrid"] == "E002"
    assert par["wrsLatitudeGrid"] == "N41"
    assert par["acquisitionType"] == "NOMINAL"
    angles = par["acquisitionAngles"]
    assert angles["illuminationAzimuthAngle"] == 152.81
    assert angles["illuminationElevationAngle"] == 57.42
    assert angles["acrossTrackIncidenceAngle"] == 9.63
    assert angles["alongTrackIncidenceAngle"] == 4.21
    assert par["beginningDateTime"] == "2021-05-03T10:49:00.000Z"
    assert par["endingDateTime"] == par["beginningDateTime"]
    assert props["created"] == "2022-03-11T09:12:45.000Z"
    assert props["productInformation"]["productType"] == "NEO_MS__2_"
    assert isinstance(props["productInformation"]["size"], int)
    assert props["productInformation"]["size"] > 0
    lineage = props["productInformation"]["resourceLineage"]["processStep"]
    assert lineage["description"] == "EOPF-EOS Converter for PLEIADES NEO"
    assert lineage["reference"]["title"] == "EOPF-EOS Specialization for PLEIADES NEO products"
    assert lineage["source"]["citation"] == NATIVE_ZIP_NAME
    assert lineage["source"]["processedLevel"] == "2_"
    assert lineage["output"]["sourceCitation"]["title"] == "%s.ZIP" % EO_PRODUCT_NAME


def test_no_pleiades_values_leaked(tmp_path):
    prod, met = _extract(tmp_path)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    # exact-value twin check: every mission-branded slot must be the PNEO one
    acq = feature["properties"]["acquisitionInformation"]
    lineage = feature["properties"]["productInformation"]["resourceLineage"]["processStep"]
    assert acq["platform"]["platformShortName"] == "PLEIADES NEO"
    assert lineage["description"] == "EOPF-EOS Converter for PLEIADES NEO"
    assert lineage["reference"]["title"] == "EOPF-EOS Specialization for PLEIADES NEO products"
    assert lineage["processingInformation"]["softwareReference"]["title"] == \
        "EOPF-EOS Converter for PLEIADES NEO"
    assert feature["properties"]["productInformation"]["productType"].startswith("NEO_")
    blob = json.dumps(feature)
    for tok in PLEIADES_TOKENS:
        assert tok not in blob, "Pleiades token leaked into PNEO output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = _extract(tmp_path)
    json_emitter.emit(met, prod, EO_PRODUCT_NAME, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % EO_PRODUCT_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
