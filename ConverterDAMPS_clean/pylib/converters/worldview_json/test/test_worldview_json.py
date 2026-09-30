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

# spec-faithful synthetic EO product name (L2AVRR_PAN product type)
EO_PRODUCT_NAME = "WV1_OPER_L2AVRR_PAN_20100527T231608_20100527T231609_0001"


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
    feature = json_template.build(mission, dynamic, template_path=json_emitter.TEMPLATE_PATH)

    # no unfilled "<...>" template placeholder survives (raises on failure)
    json_template.validate(feature)

    out_path = json_template.write_json(feature, str(out), EO_PRODUCT_NAME)
    assert os.path.exists(out_path)
    assert out_path.endswith(".JSON")

    # spot-check key reconciled fields
    assert feature["type"] == "Feature"
    assert feature["id"] == EO_PRODUCT_NAME
    props = feature["properties"]
    assert props["status"] == "ACQUIRED"
    acq = props["acquisitionInformation"][0]
    assert acq["platform"]["orbitType"] == "LEO"
    assert acq["acquisitionParameters"][0]["wavelengths"] == [{
        "spectralRange": "VNIR", "startWavelength": 450e-9, "stopWavelength": 900e-9,
        "discreteWavelengths": [675e-9]}]
    assert acq["platform"]["platformShortName"] == "WorldView-1"
    assert acq["instrument"]["instrumentShortName"] == "WorldView-60 Camera"
    assert acq["acquisitionParameters"][0]["operationalMode"] == "PAN"
    assert props["productInformation"]["productType"] == "L2AVRR_PAN"  # fixture imageDescriptor ORStandard2A
    pinfo = props["productInformation"]
    assert pinfo["processingLevel"] == "2A"  # native LV2A
    assert pinfo["processingDate"] == props["created"]
    # L2AVRR_*: CRS optional, and the fixture carries no map projection
    assert "referenceSystemIdentifier" not in pinfo
    source = pinfo["resourceLineage"][0]["processStep"][0]["source"][0]
    assert source["sourceCitation"]["title"] == prod.origName
    assert source["processedLevel"]["code"] == "LV2A"
    links = props["links"]
    assert links["measurements"][0]["type"] == "image/tiff; application=geotiff"
    assert links["measurements"][0]["title"] == "Native EO Product"
    assert links["preview"][0]["title"] == "Preview Image"
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
