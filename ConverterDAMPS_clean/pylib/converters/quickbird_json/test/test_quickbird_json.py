"""End-to-end: drive quickbird_json extraction on a synthetic native
QuickBird-2 product, emit the JSON manifest via the common template generator,
assert no template placeholder survives and key values match the template.
Also asserts no WorldView value leaked in.

Fixture is SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md).
"""
import json
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from quickbird_json import product_quickbird, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_qb2"
README_XML = FIXTURE_DIR / "010787518010_01_README.XML"

EO_PRODUCT_NAME = "QB2_OPER_BGI_PAN_2A_20100527T231608_N13-756_W100-000_0001"

WORLDVIEW_TOKENS = [
    "WorldView", "WV6", "WV1_", "WV2", "WV3", "WV4", "WVL", "Legion",
    "WorldView-60", "WorldView-110", "SpaceView", "MS4B", "MS8B", "PANCHROMATIC",
    "GeoEye", "GE01", "GIS_",
]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(work_folder):
    prod = product_quickbird.Product_Quickbird(str(README_XML))
    prod.setDebug(0)
    pi = _ProcessInfoStub(str(work_folder))
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, pi)
    return prod, met


def test_emitted_json_matches_template(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()

    prod, met = _extract(work)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic)
    json_template.validate(feature)

    out_path = json_template.write_json(feature, str(out), EO_PRODUCT_NAME)
    assert out_path.endswith(".JSON")

    props = feature["properties"]
    assert feature["type"] == "Feature"
    assert props["status"] == "ARCHIVED"
    assert props["acquisitionInformation"]["platform"]["platformShortName"] == "QuickBird-2"
    assert props["acquisitionInformation"]["platform"]["orbitType"] == "LEO"
    assert props["acquisitionInformation"]["instrument"]["instrumentShortName"] == "BGI"
    assert props["acquisitionInformation"]["acquisitionParameters"]["operationalMode"] == "PAN"
    assert props["productInformation"]["productType"] == "BGI_PAN_2A"
    assert feature["geometry"]["type"] == "Polygon"
    assert "bbox" not in feature


def test_no_worldview_or_geoeye_value_leaked(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, met = _extract(work)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic)
    blob = json.dumps(feature)
    for tok in WORLDVIEW_TOKENS:
        assert tok not in blob, "Foreign-mission token leaked into QuickBird-2 output: %s" % tok


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
