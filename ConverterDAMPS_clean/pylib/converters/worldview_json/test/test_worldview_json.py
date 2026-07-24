"""End-to-end: drive the worldview_json extraction on a synthetic native
WorldView product, emit the JSON manifest via the common template generator,
assert no template placeholder survives and key values match the template.

The fixture is SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md) — no real
native WorldView product ships with either converter.
"""
import os
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from worldview_json import product_worldview, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_wv"
README_XML = FIXTURE_DIR / "010787518010_01_README.XML"

# spec-faithful synthetic EO product name (WV6_PAN_2A type code)
EO_PRODUCT_NAME = "WV1_OPER_WV6_PAN_2A_20100527T231608_N13-756_W100-000_0001"


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(work_folder):
    prod = product_worldview.Product_Worldview(str(README_XML))
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

    # no unfilled "<...>" template placeholder survives (raises on failure)
    json_template.validate(feature)

    out_path = json_template.write_json(feature, str(out), EO_PRODUCT_NAME)
    assert os.path.exists(out_path)
    assert out_path.endswith(".JSON")

    # spot-check key reconciled fields
    assert feature["type"] == "Feature"
    assert feature["id"] == EO_PRODUCT_NAME
    props = feature["properties"]
    assert props["status"] == "ARCHIVED"
    assert props["acquisitionInformation"]["platform"]["orbitType"] == "LEO"
    assert props["acquisitionInformation"]["acquisitionParameters"]["wavelengths"]["spectralRange"] == "VIS"
    assert props["acquisitionInformation"]["platform"]["platformShortName"] == "WorldView-1"
    assert props["acquisitionInformation"]["instrument"]["instrumentShortName"] == "WorldView-60 Camera"
    assert props["acquisitionInformation"]["acquisitionParameters"]["operationalMode"] == "PANCHROMATIC"
    assert props["productInformation"]["productType"] == "WV6_PAN_2A"
    # non-MP type -> Polygon geometry, no bbox
    assert feature["geometry"]["type"] == "Polygon"
    assert "bbox" not in feature


def test_only_json_written_to_output_dir(tmp_path):
    """Emission writes exactly one .JSON and no XML / .SIP.ZIP artefact."""
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()

    prod, met = _extract(work)
    json_emitter.emit(met, prod, EO_PRODUCT_NAME, str(out))

    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % EO_PRODUCT_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
