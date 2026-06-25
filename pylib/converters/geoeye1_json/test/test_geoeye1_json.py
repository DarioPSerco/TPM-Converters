"""End-to-end: drive geoeye1_json extraction on a synthetic native GeoEye-1
product, emit the JSON manifest, assert it validates against
schema/geoeye1.schema.json. Also asserts no WorldView value leaked in.

Fixture is SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md).
"""
import json
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M
from geoeye1_json import product_geoeye1, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_ge1"
README_XML = FIXTURE_DIR / "010787518010_01_README.XML"

EO_PRODUCT_NAME = "GE1_OPER_GIS_PAN_2A_20100527T231608_N13-756_W100-000_0001"

# tokens that must NEVER appear in GeoEye-1 output (WorldView leakage guard)
WORLDVIEW_TOKENS = [
    "WorldView", "WV6", "WV1_", "WV2", "WV3", "WV4", "WVL", "Legion",
    "WorldView-60", "WorldView-110", "SpaceView", "MS4B", "MS8B", "PANCHROMATIC",
]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(work_folder):
    prod = product_geoeye1.Product_Geoeye1(str(README_XML))
    prod.setDebug(0)
    pi = _ProcessInfoStub(str(work_folder))
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, pi)
    return prod, met


def test_emitted_json_validates_against_schema(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()

    prod, met = _extract(work)
    feature = json_emitter.build_feature(met, prod, EO_PRODUCT_NAME)
    json_emitter.validate(feature)

    out_path = json_emitter.write_json(feature, str(out), EO_PRODUCT_NAME)
    assert out_path.endswith(".JSON")

    props = feature["properties"]
    assert feature["type"] == "Feature"
    assert props["acquisitionInformation"]["platform"]["platformShortName"] == "GeoEye-1"
    assert props["acquisitionInformation"]["instrument"]["instrumentShortName"] == "GIS"
    assert props["acquisitionInformation"]["acquisitionParameters"]["operationalMode"] == "PAN"
    assert props["productInformation"]["productType"] == "GIS_PAN_2A"
    assert feature["geometry"]["type"] == "Polygon"
    assert "bbox" not in feature


def test_no_worldview_value_leaked(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, met = _extract(work)
    feature = json_emitter.build_feature(met, prod, EO_PRODUCT_NAME)
    blob = json.dumps(feature)
    for tok in WORLDVIEW_TOKENS:
        assert tok not in blob, "WorldView token leaked into GeoEye-1 output: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()
    prod, met = _extract(work)
    json_emitter.emit(met, prod, EO_PRODUCT_NAME, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % EO_PRODUCT_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
